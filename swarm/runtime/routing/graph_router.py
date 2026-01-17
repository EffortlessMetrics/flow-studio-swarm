"""Graph-constrained routing with optional LLM tie-breaker."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from swarm.runtime.routing_helpers import (
    MicroloopState,
    exit_reason_needs_human_review,
    exit_reason_to_confidence,
    should_exit_microloop,
)

from .base import (
    ConditionEval,
    DecisionType,
    Edge,
    FlowGraph,
    RouteContext,
    RouteDecision,
    StepOutput,
)
from .cel_evaluator import CELEvaluator

logger = logging.getLogger(__name__)


class SmartRouter:
    """Graph-constrained router with LLM tie-breaker."""

    def __init__(
        self,
        llm_tiebreaker: Optional[Callable[[List[Edge], RouteContext], str]] = None,
        confidence_threshold: float = 0.7,
    ):
        """Initialize the SmartRouter."""
        self._cel_evaluator = CELEvaluator()
        self._llm_tiebreaker = llm_tiebreaker
        self._confidence_threshold = confidence_threshold

    def route(
        self,
        current_node: str,
        graph: FlowGraph,
        step_output: StepOutput,
        context: RouteContext,
    ) -> RouteDecision:
        """Determine the next node based on routing priority."""
        logger.debug("Routing from %s with status=%s", current_node, step_output.status)

        all_edges = graph.get_outgoing_edges(current_node)

        if not all_edges:
            return RouteDecision(
                next_node_id=None,
                decision_type=DecisionType.FLOW_COMPLETE,
                reasoning=f"No outgoing edges from {current_node}",
            )

        eval_context = self._build_eval_context(current_node, graph, step_output, context)

        if step_output.next_step_id:
            result = self._try_explicit_routing(step_output.next_step_id, all_edges, eval_context)
            if result:
                return result

        result = self._check_exit_conditions(current_node, graph, step_output, context, all_edges)
        if result:
            return result

        result = self._try_deterministic_routing(all_edges, eval_context)
        if result:
            return result

        valid_edges, evaluated = self._evaluate_edge_conditions(all_edges, eval_context)

        if len(valid_edges) == 0:
            return RouteDecision(
                next_node_id=None,
                decision_type=DecisionType.FLOW_COMPLETE,
                reasoning="No edge conditions matched",
                evaluated_conditions=evaluated,
            )

        if len(valid_edges) == 1:
            edge = valid_edges[0]
            return RouteDecision(
                next_node_id=edge.to_node,
                decision_type=DecisionType.CEL,
                reasoning=f"Single edge matched: {edge.edge_id}",
                evaluated_conditions=evaluated,
            )

        return self._invoke_llm_tiebreaker(valid_edges, context, evaluated)

    def evaluate_edge_condition(
        self,
        edge: Edge,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate a single edge condition."""
        if edge.condition is None:
            return True, None

        return self._cel_evaluator.evaluate_condition(edge.condition, context)

    def get_valid_edges(
        self,
        node: str,
        graph: FlowGraph,
        context: Dict[str, Any],
    ) -> List[Edge]:
        """Get all valid edges from a node given the context."""
        all_edges = graph.get_outgoing_edges(node)
        valid = []

        for edge in all_edges:
            result, _ = self.evaluate_edge_condition(edge, context)
            if result:
                valid.append(edge)

        return valid

    def invoke_llm_tiebreaker(
        self,
        valid_edges: List[Edge],
        context: RouteContext,
    ) -> str:
        """Invoke the LLM to break a tie between valid edges."""
        if not valid_edges:
            raise ValueError("No valid edges to choose from")

        if self._llm_tiebreaker:
            chosen_id = self._llm_tiebreaker(valid_edges, context)

            valid_targets = {e.to_node for e in valid_edges}
            if chosen_id not in valid_targets:
                logger.warning(
                    "LLM returned invalid target %s, falling back to first edge", chosen_id
                )
                chosen_id = self._get_default_edge(valid_edges).to_node

            return chosen_id

        return self._get_default_edge(valid_edges).to_node

    def _build_eval_context(
        self,
        current_node: str,
        graph: FlowGraph,
        step_output: StepOutput,
        context: RouteContext,
    ) -> Dict[str, Any]:
        """Build the evaluation context for CEL expressions."""
        node_config = graph.get_node(current_node)
        iteration_count = context.get_iteration_count(current_node)
        max_iterations = (
            node_config.max_iterations
            if node_config and node_config.max_iterations
            else graph.get_max_loop_iterations()
        )

        return {
            "status": step_output.status,
            "next_step_id": step_output.next_step_id,
            "proposed_action": step_output.proposed_action,
            "can_further_iteration_help": step_output.can_further_iteration_help,
            "iteration_count": iteration_count,
            "max_iterations": max_iterations,
            "run_id": context.run_id,
            "flow_key": context.flow_key,
            "context": context.annotations,
            "output": step_output.custom_fields,
            **step_output.custom_fields,
        }

    def _try_explicit_routing(
        self,
        target_id: str,
        edges: List[Edge],
        eval_context: Dict[str, Any],
    ) -> Optional[RouteDecision]:
        """Try explicit routing if step output specifies next_step_id."""
        valid_targets = {e.to_node for e in edges}
        if target_id in valid_targets:
            return RouteDecision(
                next_node_id=target_id,
                decision_type=DecisionType.EXPLICIT,
                reasoning=f"Step output explicitly requested: {target_id}",
            )

        logger.warning("Explicit target %s is not a valid edge, ignoring", target_id)
        return None

    def _check_exit_conditions(
        self,
        current_node: str,
        graph: FlowGraph,
        step_output: StepOutput,
        context: RouteContext,
        edges: List[Edge],
    ) -> Optional[RouteDecision]:
        """Check exit conditions for microloops."""
        node_config = graph.get_node(current_node)
        iteration_count = context.get_iteration_count(current_node)
        max_iterations = (
            node_config.max_iterations
            if node_config and node_config.max_iterations
            else graph.get_max_loop_iterations()
        )

        success_values = ["VERIFIED"]
        if node_config and node_config.exit_on:
            exit_on = node_config.exit_on
            if "status" in exit_on:
                status_values = exit_on["status"]
                if isinstance(status_values, list):
                    success_values = status_values
                elif isinstance(status_values, str):
                    success_values = [status_values]

        can_help = step_output.can_further_iteration_help
        if can_help is None:
            can_help_str = "yes"
        elif isinstance(can_help, bool):
            can_help_str = "yes" if can_help else "no"
        else:
            can_help_str = str(can_help)

        state = MicroloopState(
            current_iteration=iteration_count,
            max_iterations=max_iterations,
            status=step_output.status,
            can_further_iteration_help=can_help_str,
            success_values=success_values,
        )

        should_exit, reason = should_exit_microloop(state)

        if not should_exit:
            loop_edges = [e for e in edges if e.edge_type == "loop"]
            if loop_edges:
                context.increment_iteration(current_node)
            return None

        exit_reason_map = {
            "status_verified": f"status={step_output.status}",
            "max_iterations_reached": f"max_iterations={max_iterations}",
            "no_further_help": "can_further_iteration_help=false",
        }
        exit_reason = exit_reason_map.get(reason, reason)

        exit_edges = [e for e in edges if e.edge_type != "loop"]
        if exit_edges:
            exit_edge = self._get_default_edge(exit_edges)
            return RouteDecision(
                next_node_id=exit_edge.to_node,
                decision_type=DecisionType.EXIT_CONDITION,
                reasoning=f"Exit condition met: {exit_reason}",
                loop_count=iteration_count,
                confidence=exit_reason_to_confidence(reason),
                needs_human=exit_reason_needs_human_review(reason),
            )

        return RouteDecision(
            next_node_id=None,
            decision_type=DecisionType.EXIT_CONDITION,
            reasoning=f"Exit condition met ({exit_reason}), no exit edge",
            loop_count=iteration_count,
            confidence=exit_reason_to_confidence(reason),
            needs_human=exit_reason_needs_human_review(reason),
        )

    def _try_deterministic_routing(
        self,
        edges: List[Edge],
        eval_context: Dict[str, Any],
    ) -> Optional[RouteDecision]:
        """Try deterministic routing (single edge or unconditional edge)."""
        if len(edges) == 1:
            edge = edges[0]
            if edge.condition:
                result, err = self.evaluate_edge_condition(edge, eval_context)
                if not result:
                    return RouteDecision(
                        next_node_id=None,
                        decision_type=DecisionType.FLOW_COMPLETE,
                        reasoning=f"Single edge condition failed: {err}",
                        evaluated_conditions=[
                            ConditionEval(
                                edge_id=edge.edge_id,
                                expression=str(edge.condition.expression or edge.condition.field),
                                result=False,
                                error=err,
                            )
                        ],
                    )

            return RouteDecision(
                next_node_id=edge.to_node,
                decision_type=DecisionType.DETERMINISTIC,
                reasoning=f"Single outgoing edge: {edge.edge_id}",
            )

        unconditional = [e for e in edges if e.condition is None]
        if len(unconditional) == 1:
            edge = unconditional[0]
            return RouteDecision(
                next_node_id=edge.to_node,
                decision_type=DecisionType.DETERMINISTIC,
                reasoning=f"Single unconditional edge: {edge.edge_id}",
            )

        return None

    def _evaluate_edge_conditions(
        self,
        edges: List[Edge],
        eval_context: Dict[str, Any],
    ) -> Tuple[List[Edge], List[ConditionEval]]:
        """Evaluate conditions for all edges."""
        valid_edges: List[Edge] = []
        evaluated: List[ConditionEval] = []

        sorted_edges = sorted(edges, key=lambda e: e.priority, reverse=True)

        for edge in sorted_edges:
            expression_str = ""
            if edge.condition:
                expression_str = (
                    edge.condition.expression
                    or f"{edge.condition.field} {edge.condition.operator} {edge.condition.value}"
                )

            result, err = self.evaluate_edge_condition(edge, eval_context)

            evaluated.append(
                ConditionEval(
                    edge_id=edge.edge_id,
                    expression=expression_str or "(unconditional)",
                    result=result,
                    error=err,
                )
            )

            if result:
                valid_edges.append(edge)

        return valid_edges, evaluated

    def _invoke_llm_tiebreaker(
        self,
        valid_edges: List[Edge],
        context: RouteContext,
        evaluated: List[ConditionEval],
    ) -> RouteDecision:
        """Invoke LLM tie-breaker for multiple valid edges."""
        try:
            chosen_target = self.invoke_llm_tiebreaker(valid_edges, context)

            confidence = 0.9 if self._llm_tiebreaker else 0.7
            needs_human = confidence < self._confidence_threshold

            return RouteDecision(
                next_node_id=chosen_target,
                decision_type=DecisionType.LLM_TIEBREAKER,
                reasoning=f"LLM chose {chosen_target} from {len(valid_edges)} valid edges",
                evaluated_conditions=evaluated,
                confidence=confidence,
                needs_human=needs_human,
            )
        except Exception as e:
            logger.warning("LLM tie-breaker failed: %s", e)

            default_edge = self._get_default_edge(valid_edges)
            return RouteDecision(
                next_node_id=default_edge.to_node,
                decision_type=DecisionType.ERROR,
                reasoning=f"LLM tie-breaker failed ({e}), using default: {default_edge.edge_id}",
                evaluated_conditions=evaluated,
                confidence=0.5,
                needs_human=True,
            )

    def _get_default_edge(self, edges: List[Edge]) -> Edge:
        """Get the default edge by priority."""
        if not edges:
            raise ValueError("No edges to select from")

        sorted_edges = sorted(edges, key=lambda e: (-e.priority, e.edge_id))
        return sorted_edges[0]


def create_router(
    llm_tiebreaker: Optional[Callable[[List[Edge], RouteContext], str]] = None,
) -> SmartRouter:
    """Create a SmartRouter with optional LLM tie-breaker."""
    return SmartRouter(llm_tiebreaker=llm_tiebreaker)


def route_step(
    current_node: str,
    graph: FlowGraph,
    step_output: StepOutput,
    context: RouteContext,
    router: Optional[SmartRouter] = None,
) -> RouteDecision:
    """Convenience function for routing a step."""
    if router is None:
        router = SmartRouter()

    return router.route(current_node, graph, step_output, context)
