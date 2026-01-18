"""WP4 stepwise router and audit helpers."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from swarm.runtime.routing_helpers import MicroloopState, should_exit_microloop

from .base import Edge, FlowGraph, RunContext, RoutingContext, RoutingResult
from .cel_evaluator import CELEvaluator

logger = logging.getLogger(__name__)


class StepRouter:
    """Bounded, auditable, cheap router for stepwise flow execution."""

    def __init__(
        self,
        llm_tiebreaker: Optional[Callable[[List[Edge], RunContext], Tuple[str, str]]] = None,
    ):
        """Initialize the StepRouter."""
        self._cel_evaluator = CELEvaluator()
        self._llm_tiebreaker = llm_tiebreaker

    def route(
        self,
        current_node: str,
        flow_graph: FlowGraph,
        context: RunContext,
    ) -> RoutingResult:
        """Route from current node to next step."""
        import time

        start_time = time.time()

        elimination_log: List[Dict[str, Any]] = []

        candidates = self.get_adjacent_edges(current_node, flow_graph)
        edges_considered = len(candidates)

        if not candidates:
            elapsed_ms = (time.time() - start_time) * 1000
            return RoutingResult(
                edge=None,
                method="no_candidates",
                terminate=True,
                needs_human=False,
                explanation=self._build_explanation(
                    decision="Flow complete - no outgoing edges",
                    candidates_evaluated=0,
                    elimination_log=elimination_log,
                    selected_edge="",
                    method="no_candidates",
                    edges_considered=edges_considered,
                    time_ms=elapsed_ms,
                ),
            )

        candidates, exit_eliminations = self.filter_exit_conditions(
            candidates, context, flow_graph, current_node
        )
        elimination_log.extend(exit_eliminations)

        candidates, cel_eliminations = self.filter_conditions(candidates, context, current_node)
        elimination_log.extend(cel_eliminations)

        elapsed_ms = (time.time() - start_time) * 1000

        if len(candidates) == 0:
            return RoutingResult(
                edge=None,
                method="no_candidates",
                terminate=True,
                needs_human=True,
                explanation=self._build_explanation(
                    decision="No valid edges after condition evaluation",
                    candidates_evaluated=edges_considered,
                    elimination_log=elimination_log,
                    selected_edge="",
                    method="no_candidates",
                    edges_considered=edges_considered,
                    time_ms=elapsed_ms,
                ),
            )

        if len(candidates) == 1:
            edge = candidates[0]
            return RoutingResult(
                edge=edge,
                method="deterministic",
                terminate=False,
                needs_human=False,
                explanation=self._build_explanation(
                    decision=f"Single valid edge: {edge.edge_id}",
                    candidates_evaluated=edges_considered,
                    elimination_log=elimination_log,
                    selected_edge=edge.edge_id,
                    method="deterministic",
                    edges_considered=edges_considered,
                    time_ms=elapsed_ms,
                ),
            )

        return self.llm_tiebreak(
            candidates, context, elimination_log, edges_considered, start_time
        )

    def get_adjacent_edges(self, node_id: str, flow_graph: FlowGraph) -> List[Edge]:
        """Get all edges originating from a node."""
        edges = flow_graph.get_outgoing_edges(node_id)
        return sorted(edges, key=lambda e: (-e.priority, e.edge_id))

    def filter_exit_conditions(
        self,
        candidates: List[Edge],
        context: RunContext,
        flow_graph: FlowGraph,
        current_node: str,
    ) -> Tuple[List[Edge], List[Dict[str, Any]]]:
        """Apply exit conditions to filter candidates."""
        elimination_log: List[Dict[str, Any]] = []
        iteration_count = context.iteration_counts.get(current_node, 0)
        max_iterations = self._resolve_max_iterations(flow_graph, context, current_node)

        status = context.get("status", "")
        can_help = context.get("can_further_iteration_help", True)

        if can_help is None:
            can_help_str = "yes"
        elif isinstance(can_help, bool):
            can_help_str = "yes" if can_help else "no"
        else:
            can_help_str = str(can_help)

        state = MicroloopState(
            current_iteration=iteration_count,
            max_iterations=max_iterations,
            status=str(status).upper() if status else "",
            can_further_iteration_help=can_help_str,
        )

        should_exit, reason = should_exit_microloop(state)

        if should_exit:
            exit_reason_map = {
                "status_verified": "status=VERIFIED",
                "max_iterations_reached": f"max_iterations={max_iterations}",
                "no_further_help": "can_further_iteration_help=false",
            }
            exit_reason = exit_reason_map.get(reason, reason)

            remaining = []
            for edge in candidates:
                if edge.edge_type == "loop":
                    elimination_log.append(
                        {
                            "edge_id": edge.edge_id,
                            "reason": f"Exit condition met: {exit_reason}",
                            "stage": "condition",
                        }
                    )
                else:
                    remaining.append(edge)
            return remaining, elimination_log

        return candidates, elimination_log

    def _resolve_max_iterations(
        self,
        flow_graph: FlowGraph,
        context: RunContext,
        current_node: str,
    ) -> int:
        """Resolve max iterations from node override, policy default, and runtime fuse."""
        node_config = flow_graph.get_node(current_node)
        policy_max = flow_graph.get_max_loop_iterations()
        node_max = (
            node_config.max_iterations
            if node_config and node_config.max_iterations is not None
            else policy_max
        )
        runtime_max = context.max_iterations
        if runtime_max is None:
            return node_max
        return min(node_max, runtime_max)

    def filter_conditions(
        self,
        candidates: List[Edge],
        context: RunContext,
        current_node: str,
    ) -> Tuple[List[Edge], List[Dict[str, Any]]]:
        """Apply CEL/condition evaluation to filter candidates."""
        elimination_log: List[Dict[str, Any]] = []
        remaining: List[Edge] = []

        eval_context = {
            "status": context.get("status", ""),
            "can_further_iteration_help": context.get("can_further_iteration_help", True),
            "iteration_count": context.iteration_counts.get(current_node, 0),
            "run_id": context.run_id,
            "flow_key": context.flow_key,
            **context.step_output,
            **context.annotations,
        }

        for edge in candidates:
            if edge.condition is None:
                remaining.append(edge)
                continue

            result, error = self._cel_evaluator.evaluate_condition(edge.condition, eval_context)

            if result:
                remaining.append(edge)
            else:
                elimination_log.append(
                    {
                        "edge_id": edge.edge_id,
                        "reason": error or "Condition evaluated to false",
                        "stage": "condition",
                    }
                )

        return remaining, elimination_log

    def llm_tiebreak(
        self,
        candidates: List[Edge],
        context: RunContext,
        elimination_log: List[Dict[str, Any]],
        edges_considered: int,
        start_time: float,
    ) -> RoutingResult:
        """Use LLM to break tie between multiple valid edges."""
        import time

        if self._llm_tiebreaker:
            try:
                target_id, reasoning = self._llm_tiebreaker(candidates, context)

                valid_targets = {e.to_node: e for e in candidates}
                selected_edge = valid_targets.get(target_id)

                if selected_edge is None:
                    logger.warning(
                        "LLM returned invalid target %s, using priority fallback", target_id
                    )
                    selected_edge = candidates[0]
                    reasoning = "LLM returned invalid target, using priority fallback"

                for edge in candidates:
                    if edge.edge_id != selected_edge.edge_id:
                        elimination_log.append(
                            {
                                "edge_id": edge.edge_id,
                                "reason": "Not selected by LLM tiebreaker",
                                "stage": "llm_tiebreak",
                            }
                        )

                elapsed_ms = (time.time() - start_time) * 1000
                return RoutingResult(
                    edge=selected_edge,
                    method="llm_tiebreak",
                    terminate=False,
                    needs_human=False,
                    explanation=self._build_explanation(
                        decision=f"LLM selected: {selected_edge.edge_id}",
                        candidates_evaluated=edges_considered,
                        elimination_log=elimination_log,
                        selected_edge=selected_edge.edge_id,
                        method="llm_tiebreak",
                        llm_reasoning=reasoning,
                        edges_considered=edges_considered,
                        time_ms=elapsed_ms,
                    ),
                )

            except Exception as e:
                logger.warning("LLM tiebreaker failed: %s", e)

        selected_edge = candidates[0]
        for edge in candidates[1:]:
            elimination_log.append(
                {
                    "edge_id": edge.edge_id,
                    "reason": f"Lower priority than {selected_edge.edge_id}",
                    "stage": "priority",
                }
            )

        elapsed_ms = (time.time() - start_time) * 1000
        return RoutingResult(
            edge=selected_edge,
            method="deterministic",
            terminate=False,
            needs_human=True,
            explanation=self._build_explanation(
                decision=f"Priority fallback: {selected_edge.edge_id}",
                candidates_evaluated=edges_considered,
                elimination_log=elimination_log,
                selected_edge=selected_edge.edge_id,
                method="deterministic",
                edges_considered=edges_considered,
                time_ms=elapsed_ms,
            ),
        )

    def _build_explanation(
        self,
        decision: str,
        candidates_evaluated: int,
        elimination_log: List[Dict[str, Any]],
        selected_edge: str,
        method: str,
        edges_considered: int,
        time_ms: float,
        llm_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build structured explanation for audit trail."""
        explanation: Dict[str, Any] = {
            "decision": decision,
            "candidates_evaluated": candidates_evaluated,
            "elimination_log": elimination_log,
            "selected_edge": selected_edge,
            "method": method,
            "metrics": {
                "edges_considered": edges_considered,
                "time_ms": round(time_ms, 2),
            },
        }

        if llm_reasoning:
            explanation["llm_reasoning"] = llm_reasoning

        return explanation


def store_routing_audit(
    envelope: Any,
    routing_result: RoutingResult,
) -> None:
    """Store routing explanation on the handoff envelope."""
    if routing_result.explanation:
        envelope.routing_audit = routing_result.explanation


def emit_routing_event(
    run_id: str,
    flow_key: str,
    step_id: str,
    routing_result: RoutingResult,
    append_event_fn: Optional[Callable] = None,
) -> None:
    """Emit a routing decision event to the events table."""
    from datetime import datetime, timezone
    from swarm.runtime.types import RunEvent

    if append_event_fn is None:
        from swarm.runtime.storage import append_event as append_event_fn

    event = RunEvent(
        run_id=run_id,
        ts=datetime.now(timezone.utc),
        kind="route_decision",
        flow_key=flow_key,
        step_id=step_id,
        payload={
            "method": routing_result.method,
            "selected_edge": routing_result.edge.edge_id if routing_result.edge else "",
            "target_node": routing_result.edge.to_node if routing_result.edge else "",
            "terminate": routing_result.terminate,
            "needs_human": routing_result.needs_human,
            "explanation": routing_result.explanation,
        },
    )
    append_event_fn(run_id, event)


def route_from_step(
    flow_graph: FlowGraph,
    current_node: str,
    step_output: Dict[str, Any],
    context: RoutingContext,
    llm_tiebreaker: Optional[Callable[[List[Edge], RoutingContext], Tuple[str, str]]] = None,
) -> RoutingResult:
    """Route from current step to next step using bounded, auditable routing."""
    run_ctx = RunContext(
        run_id=context.run_id,
        flow_key=context.flow_key,
        step_output=step_output,
        iteration_counts=context.iteration_counts,
        max_iterations=context.max_iterations,
        annotations=context.annotations,
    )

    adapted_tiebreaker = None
    if llm_tiebreaker:

        def adapted_tiebreaker(edges: List[Edge], ctx: RunContext) -> Tuple[str, str]:
            routing_ctx = RoutingContext(
                run_id=ctx.run_id,
                flow_key=ctx.flow_key,
                current_node=current_node,
                iteration_counts=ctx.iteration_counts,
                max_iterations=ctx.max_iterations,
                annotations=ctx.annotations,
            )
            return llm_tiebreaker(edges, routing_ctx)

    router = StepRouter(llm_tiebreaker=adapted_tiebreaker)
    result = router.route(current_node, flow_graph, run_ctx)

    return result


def convert_to_wp4_explanation(
    routing_result: RoutingResult,
) -> Dict[str, Any]:
    """Convert RoutingResult explanation to WP4RoutingExplanation format."""
    from swarm.runtime.types import (
        WP4EliminationEntry,
        WP4RoutingExplanation,
        WP4RoutingMetrics,
        wp4_routing_explanation_to_dict,
    )

    if not routing_result.explanation:
        return wp4_routing_explanation_to_dict(
            WP4RoutingExplanation(
                decision="No explanation available",
                method=routing_result.method,
                selected_edge=routing_result.edge.edge_id if routing_result.edge else "",
                candidates_evaluated=0,
            )
        )

    explanation = routing_result.explanation

    elimination_log = [
        WP4EliminationEntry(
            edge_id=entry.get("edge_id", ""),
            reason=entry.get("reason", ""),
            stage=entry.get("stage", "condition"),
        )
        for entry in explanation.get("elimination_log", [])
    ]

    metrics_data = explanation.get("metrics", {})
    metrics = WP4RoutingMetrics(
        edges_considered=metrics_data.get("edges_considered", 0),
        time_ms=metrics_data.get("time_ms", 0.0),
        llm_tokens_used=metrics_data.get("llm_tokens_used", 0),
    )

    wp4_explanation = WP4RoutingExplanation(
        decision=explanation.get("decision", ""),
        method=explanation.get("method", routing_result.method),
        selected_edge=explanation.get("selected_edge", ""),
        candidates_evaluated=explanation.get("candidates_evaluated", 0),
        elimination_log=elimination_log,
        llm_reasoning=explanation.get("llm_reasoning"),
        metrics=metrics,
    )

    return wp4_routing_explanation_to_dict(wp4_explanation)


def attach_routing_audit(
    envelope: Any,
    routing_result: RoutingResult,
    use_wp4_format: bool = True,
) -> None:
    """Attach routing explanation to a HandoffEnvelope for audit trail."""
    if routing_result.explanation:
        if use_wp4_format:
            envelope.routing_audit = convert_to_wp4_explanation(routing_result)
        else:
            envelope.routing_audit = routing_result.explanation
