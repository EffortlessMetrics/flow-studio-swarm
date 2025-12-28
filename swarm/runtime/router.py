"""
router.py - SmartRouter for graph-constrained routing with LLM tie-breaker

This module implements the graph-constrained routing system as defined in ADR-004.
The SmartRouter determines the next node in a flow execution by following a strict
priority order:

1. Explicit routing - step output specifies next_step_id
2. Exit conditions - exit_on rules (VERIFIED, max_iterations)
3. Deterministic edges - single outgoing edge, or edge with condition=true
4. CEL evaluation - evaluate edge conditions against step context
5. LLM tie-breaker - only if multiple edges remain valid

The key principle is: graph constraints are always enforced. The router can never
route to an edge not defined in the flow graph. LLM is only a tie-breaker when
deterministic rules do not resolve.

Usage:
    from swarm.runtime.router import SmartRouter, RouteContext, RouteDecision

    router = SmartRouter()
    decision = router.route(
        current_node="code-implementer",
        graph=flow_graph,
        step_output=step_output,
        context=route_context,
    )
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Core Data Types
# =============================================================================


class DecisionType(str, Enum):
    """Type of routing decision made."""

    EXPLICIT = "explicit"           # Step output specified next_step_id
    EXIT_CONDITION = "exit_condition"  # Exit condition (VERIFIED, max_iterations) met
    DETERMINISTIC = "deterministic"  # Single edge or edge with condition=true
    CEL = "cel"                     # CEL expression evaluation
    LLM_TIEBREAKER = "llm_tiebreaker"  # LLM resolved tie between valid edges
    FLOW_COMPLETE = "flow_complete"  # No valid edges, flow is complete
    ERROR = "error"                 # Routing error occurred


@dataclass
class ConditionEval:
    """Result of evaluating a single edge condition."""

    edge_id: str
    expression: str
    result: bool
    error: Optional[str] = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RouteDecision:
    """The result of a routing decision.

    Attributes:
        next_node_id: The ID of the next node to execute, or None if flow is complete.
        decision_type: How the routing decision was made.
        reasoning: Human-readable explanation of the decision.
        evaluated_conditions: List of condition evaluations performed.
        confidence: Confidence score for the decision (0.0 to 1.0).
        needs_human: Whether human review is recommended.
        loop_count: Current iteration count for microloop tracking.
    """

    next_node_id: Optional[str]
    decision_type: DecisionType
    reasoning: str
    evaluated_conditions: List[ConditionEval] = field(default_factory=list)
    confidence: float = 1.0
    needs_human: bool = False
    loop_count: int = 0


@dataclass
class StepOutput:
    """Output from a step execution relevant to routing.

    Attributes:
        status: The step's execution status (e.g., 'VERIFIED', 'UNVERIFIED', 'BLOCKED').
        next_step_id: Explicit next step if step declares it.
        proposed_action: Routing action hint from the step (PROCEED, RERUN, BOUNCE, FIX_ENV).
        can_further_iteration_help: Critic's judgment about iteration viability.
        custom_fields: Additional fields for CEL evaluation.
    """

    status: str = "UNKNOWN"
    next_step_id: Optional[str] = None
    proposed_action: Optional[str] = None
    can_further_iteration_help: Optional[bool] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a field value for CEL evaluation."""
        if key == "status":
            return self.status
        if key == "next_step_id":
            return self.next_step_id
        if key == "proposed_action":
            return self.proposed_action
        if key == "can_further_iteration_help":
            return self.can_further_iteration_help
        return self.custom_fields.get(key, default)


@dataclass
class RouteContext:
    """Context for routing decisions.

    Attributes:
        run_id: The current run identifier.
        flow_key: The flow being executed.
        iteration_counts: Map of node_id to iteration count for microloop tracking.
        max_iterations_default: Default max iterations if not specified per-node.
        previous_outputs: Map of step_id to their outputs for context.
        annotations: Arbitrary context annotations.
    """

    run_id: str
    flow_key: str
    iteration_counts: Dict[str, int] = field(default_factory=dict)
    max_iterations_default: int = 5
    previous_outputs: Dict[str, StepOutput] = field(default_factory=dict)
    annotations: Dict[str, Any] = field(default_factory=dict)

    def get_iteration_count(self, node_id: str) -> int:
        """Get the current iteration count for a node."""
        return self.iteration_counts.get(node_id, 0)

    def increment_iteration(self, node_id: str) -> int:
        """Increment and return the iteration count for a node."""
        current = self.iteration_counts.get(node_id, 0)
        self.iteration_counts[node_id] = current + 1
        return current + 1


# =============================================================================
# Graph Types (matching flow_graph.schema.json)
# =============================================================================


@dataclass
class EdgeCondition:
    """Condition for edge traversal.

    Supports both simple field comparison and CEL expressions.
    """

    field: Optional[str] = None
    operator: str = "equals"
    value: Any = None
    expression: Optional[str] = None  # CEL or simple expression


@dataclass
class Edge:
    """An edge in the flow graph."""

    edge_id: str
    from_node: str  # 'from' in schema
    to_node: str    # 'to' in schema
    condition: Optional[EdgeCondition] = None
    priority: int = 50
    edge_type: str = "sequence"  # sequence, loop, branch, detour, injection, subflow

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        """Create an Edge from a dictionary (flow_graph.schema.json format)."""
        condition = None
        if "condition" in data:
            cond_data = data["condition"]
            condition = EdgeCondition(
                field=cond_data.get("field"),
                operator=cond_data.get("operator", "equals"),
                value=cond_data.get("value"),
                expression=cond_data.get("expression"),
            )

        return cls(
            edge_id=data.get("edge_id", ""),
            from_node=data.get("from", ""),
            to_node=data.get("to", ""),
            condition=condition,
            priority=data.get("priority", 50),
            edge_type=data.get("type", "sequence"),
        )


@dataclass
class NodeConfig:
    """Configuration for a node relevant to routing."""

    node_id: str
    template_id: str
    max_iterations: Optional[int] = None
    exit_on: Optional[Dict[str, Any]] = None  # Exit conditions for microloops

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeConfig":
        """Create a NodeConfig from a dictionary."""
        params = data.get("params", {})
        overrides = data.get("overrides", {})

        # Exit conditions can come from overrides or params
        exit_on = overrides.get("exit_on") or params.get("exit_on")
        max_iterations = overrides.get("max_iterations") or params.get("max_iterations")

        return cls(
            node_id=data.get("node_id", ""),
            template_id=data.get("template_id", ""),
            max_iterations=max_iterations,
            exit_on=exit_on,
        )


@dataclass
class FlowGraph:
    """A flow graph for routing decisions.

    Attributes:
        graph_id: Unique identifier for the graph.
        nodes: Map of node_id to NodeConfig.
        edges: List of edges in the graph.
        policy: Graph-level policy settings.
    """

    graph_id: str
    nodes: Dict[str, NodeConfig]
    edges: List[Edge]
    policy: Dict[str, Any] = field(default_factory=dict)

    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        """Get all edges originating from a node."""
        return [e for e in self.edges if e.from_node == node_id]

    def get_node(self, node_id: str) -> Optional[NodeConfig]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_max_loop_iterations(self) -> int:
        """Get the default max loop iterations from policy."""
        return self.policy.get("max_loop_iterations", 5)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowGraph":
        """Create a FlowGraph from a dictionary (flow_graph.schema.json format)."""
        nodes = {}
        for node_data in data.get("nodes", []):
            node = NodeConfig.from_dict(node_data)
            nodes[node.node_id] = node

        edges = [Edge.from_dict(e) for e in data.get("edges", [])]

        return cls(
            graph_id=data.get("id", ""),
            nodes=nodes,
            edges=edges,
            policy=data.get("policy", {}),
        )


# =============================================================================
# CEL Expression Evaluator (Simple Implementation)
# =============================================================================


class CELEvaluator:
    """Simple CEL-like expression evaluator.

    Supports a subset of CEL for edge condition evaluation:
    - Comparisons: ==, !=, <, >, <=, >=
    - Boolean logic: &&, ||, !
    - String operations: contains, startsWith, endsWith
    - Field access: status, iteration_count, context.field

    For production use, consider using cel-python or similar library.
    """

    def __init__(self):
        self._operators = {
            "equals": lambda a, b: a == b,
            "not_equals": lambda a, b: a != b,
            "in": lambda a, b: a in b if isinstance(b, (list, tuple, set)) else False,
            "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple, set)) else True,
            "contains": lambda a, b: b in a if isinstance(a, str) else False,
            "gt": lambda a, b: a > b if a is not None and b is not None else False,
            "lt": lambda a, b: a < b if a is not None and b is not None else False,
            "gte": lambda a, b: a >= b if a is not None and b is not None else False,
            "lte": lambda a, b: a <= b if a is not None and b is not None else False,
            "matches": lambda a, b: bool(re.search(b, a)) if isinstance(a, str) else False,
        }

    def evaluate_condition(
        self,
        condition: EdgeCondition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate an edge condition against context.

        Args:
            condition: The edge condition to evaluate.
            context: Context dictionary for variable resolution.

        Returns:
            Tuple of (result, error_message or None).
        """
        try:
            # If there's a CEL expression, evaluate it
            if condition.expression:
                return self._evaluate_expression(condition.expression, context)

            # Otherwise, use simple field comparison
            if condition.field is None:
                # No condition means always true (unconditional edge)
                return True, None

            field_value = self._resolve_field(condition.field, context)
            operator = condition.operator
            expected_value = condition.value

            if operator not in self._operators:
                return False, f"Unknown operator: {operator}"

            op_func = self._operators[operator]
            result = op_func(field_value, expected_value)
            return result, None

        except Exception as e:
            logger.debug("Condition evaluation error: %s", e)
            return False, str(e)

    def _resolve_field(self, field_path: str, context: Dict[str, Any]) -> Any:
        """Resolve a field path in the context.

        Supports dot notation: 'context.has_errors', 'output.severity'
        """
        parts = field_path.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            elif hasattr(value, "get"):
                value = value.get(part)
            else:
                return None

            if value is None:
                return None

        return value

    def _evaluate_expression(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate a CEL-like expression.

        Supports simple expressions like:
        - status == 'VERIFIED'
        - iteration_count >= 3
        - status == 'VERIFIED' || can_further_iteration_help == false
        """
        try:
            # Normalize the expression
            expr = expression.strip()

            # Handle || (OR) - check if any sub-expression is true
            if "||" in expr:
                parts = [p.strip() for p in expr.split("||")]
                for part in parts:
                    result, err = self._evaluate_simple_expression(part, context)
                    if err is None and result:
                        return True, None
                return False, None

            # Handle && (AND) - check if all sub-expressions are true
            if "&&" in expr:
                parts = [p.strip() for p in expr.split("&&")]
                for part in parts:
                    result, err = self._evaluate_simple_expression(part, context)
                    if err is not None or not result:
                        return False, err
                return True, None

            # Simple expression
            return self._evaluate_simple_expression(expr, context)

        except Exception as e:
            return False, str(e)

    def _evaluate_simple_expression(
        self,
        expr: str,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate a simple comparison expression."""
        # Supported operators: ==, !=, >=, <=, >, <
        operators_re = r"(==|!=|>=|<=|>|<)"
        match = re.split(operators_re, expr)

        if len(match) != 3:
            return False, f"Invalid expression: {expr}"

        left = match[0].strip()
        operator = match[1]
        right = match[2].strip()

        # Resolve left side
        left_value = self._resolve_value(left, context)

        # Resolve right side
        right_value = self._resolve_value(right, context)

        # Compare
        if operator == "==":
            return left_value == right_value, None
        elif operator == "!=":
            return left_value != right_value, None
        elif operator == ">=":
            return left_value >= right_value, None
        elif operator == "<=":
            return left_value <= right_value, None
        elif operator == ">":
            return left_value > right_value, None
        elif operator == "<":
            return left_value < right_value, None

        return False, f"Unknown operator: {operator}"

    def _resolve_value(self, value_str: str, context: Dict[str, Any]) -> Any:
        """Resolve a value from string representation or context."""
        value_str = value_str.strip()

        # String literal
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]

        # Boolean
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # Numeric
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # Context field
        return self._resolve_field(value_str, context)


# =============================================================================
# SmartRouter
# =============================================================================


class SmartRouter:
    """Graph-constrained router with LLM tie-breaker.

    Implements the routing strategy from ADR-004:
    1. Explicit routing - step output specifies next_step_id
    2. Exit conditions - exit_on rules (VERIFIED, max_iterations)
    3. Deterministic edges - single outgoing edge, or edge with condition=true
    4. CEL evaluation - evaluate edge conditions against step context
    5. LLM tie-breaker - only if multiple edges remain valid

    The router never creates edges not in the graph. All routing decisions
    are constrained to valid graph edges.
    """

    def __init__(
        self,
        llm_tiebreaker: Optional[Callable[[List[Edge], RouteContext], str]] = None,
        confidence_threshold: float = 0.7,
    ):
        """Initialize the SmartRouter.

        Args:
            llm_tiebreaker: Optional callable for LLM tie-breaking.
                Takes (valid_edges, context) and returns target node_id.
                If not provided, uses first edge by priority as fallback.
            confidence_threshold: Confidence threshold below which needs_human
                is set to True.
        """
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
        """Determine the next node based on routing priority.

        Args:
            current_node: The ID of the current node.
            graph: The flow graph defining valid transitions.
            step_output: Output from the current step execution.
            context: Routing context including iteration counts.

        Returns:
            RouteDecision with the next node and decision metadata.
        """
        logger.debug(
            "Routing from %s with status=%s",
            current_node, step_output.status
        )

        # Get all outgoing edges from current node
        all_edges = graph.get_outgoing_edges(current_node)

        if not all_edges:
            # No outgoing edges = flow complete
            return RouteDecision(
                next_node_id=None,
                decision_type=DecisionType.FLOW_COMPLETE,
                reasoning=f"No outgoing edges from {current_node}",
            )

        # Build evaluation context
        eval_context = self._build_eval_context(
            current_node, graph, step_output, context
        )

        # Priority 1: Explicit routing from step output
        if step_output.next_step_id:
            result = self._try_explicit_routing(
                step_output.next_step_id, all_edges, eval_context
            )
            if result:
                return result

        # Priority 2: Exit conditions (VERIFIED, max_iterations)
        result = self._check_exit_conditions(
            current_node, graph, step_output, context, all_edges
        )
        if result:
            return result

        # Priority 3: Deterministic edges
        result = self._try_deterministic_routing(all_edges, eval_context)
        if result:
            return result

        # Priority 4: CEL evaluation
        valid_edges, evaluated = self._evaluate_edge_conditions(all_edges, eval_context)

        if len(valid_edges) == 0:
            # No valid edges found - flow complete or error
            return RouteDecision(
                next_node_id=None,
                decision_type=DecisionType.FLOW_COMPLETE,
                reasoning="No edge conditions matched",
                evaluated_conditions=evaluated,
            )

        if len(valid_edges) == 1:
            # Single valid edge after CEL evaluation
            edge = valid_edges[0]
            return RouteDecision(
                next_node_id=edge.to_node,
                decision_type=DecisionType.CEL,
                reasoning=f"Single edge matched: {edge.edge_id}",
                evaluated_conditions=evaluated,
            )

        # Priority 5: LLM tie-breaker
        return self._invoke_llm_tiebreaker(valid_edges, context, evaluated)

    def evaluate_edge_condition(
        self,
        edge: Edge,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate a single edge condition.

        Args:
            edge: The edge whose condition to evaluate.
            context: Evaluation context dictionary.

        Returns:
            Tuple of (result, error_message or None).
        """
        if edge.condition is None:
            # No condition = always valid
            return True, None

        return self._cel_evaluator.evaluate_condition(edge.condition, context)

    def get_valid_edges(
        self,
        node: str,
        graph: FlowGraph,
        context: Dict[str, Any],
    ) -> List[Edge]:
        """Get all valid edges from a node given the context.

        Args:
            node: The node ID to check edges from.
            graph: The flow graph.
            context: Evaluation context dictionary.

        Returns:
            List of edges whose conditions evaluate to true.
        """
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
        """Invoke the LLM to break a tie between valid edges.

        Args:
            valid_edges: List of valid edges to choose from.
            context: The routing context.

        Returns:
            The target node_id chosen by the LLM.

        Raises:
            ValueError: If LLM returns invalid edge.
        """
        if not valid_edges:
            raise ValueError("No valid edges to choose from")

        if self._llm_tiebreaker:
            chosen_id = self._llm_tiebreaker(valid_edges, context)

            # Validate the choice
            valid_targets = {e.to_node for e in valid_edges}
            if chosen_id not in valid_targets:
                logger.warning(
                    "LLM returned invalid target %s, falling back to first edge",
                    chosen_id
                )
                # Fall back to first edge by priority
                chosen_id = self._get_default_edge(valid_edges).to_node

            return chosen_id

        # No LLM tiebreaker configured, use priority-based fallback
        return self._get_default_edge(valid_edges).to_node

    # =========================================================================
    # Private Methods
    # =========================================================================

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
            node_config.max_iterations if node_config and node_config.max_iterations
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
        # Validate that target is a valid edge
        valid_targets = {e.to_node for e in edges}
        if target_id in valid_targets:
            return RouteDecision(
                next_node_id=target_id,
                decision_type=DecisionType.EXPLICIT,
                reasoning=f"Step output explicitly requested: {target_id}",
            )

        logger.warning(
            "Explicit target %s is not a valid edge, ignoring",
            target_id
        )
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
            node_config.max_iterations if node_config and node_config.max_iterations
            else graph.get_max_loop_iterations()
        )

        exit_reason = None

        # Check status-based exit (VERIFIED = done)
        if step_output.status == "VERIFIED":
            exit_reason = f"status=VERIFIED"

        # Check iteration limit
        elif iteration_count >= max_iterations:
            exit_reason = f"max_iterations={max_iterations}"

        # Check can_further_iteration_help
        elif step_output.can_further_iteration_help is False:
            exit_reason = "can_further_iteration_help=false"

        # Check node-specific exit_on conditions
        elif node_config and node_config.exit_on:
            exit_on = node_config.exit_on

            # Check status values
            if "status" in exit_on:
                status_values = exit_on["status"]
                if isinstance(status_values, list) and step_output.status in status_values:
                    exit_reason = f"exit_on.status={step_output.status}"
                elif isinstance(status_values, str) and step_output.status == status_values:
                    exit_reason = f"exit_on.status={step_output.status}"

        if exit_reason:
            # Find non-loop edge (exit edge)
            exit_edges = [e for e in edges if e.edge_type != "loop"]
            if exit_edges:
                # Take highest priority exit edge
                exit_edge = self._get_default_edge(exit_edges)
                return RouteDecision(
                    next_node_id=exit_edge.to_node,
                    decision_type=DecisionType.EXIT_CONDITION,
                    reasoning=f"Exit condition met: {exit_reason}",
                    loop_count=iteration_count,
                )
            else:
                # No exit edge, flow complete
                return RouteDecision(
                    next_node_id=None,
                    decision_type=DecisionType.EXIT_CONDITION,
                    reasoning=f"Exit condition met ({exit_reason}), no exit edge",
                    loop_count=iteration_count,
                )

        # Increment iteration count for loop edges
        loop_edges = [e for e in edges if e.edge_type == "loop"]
        if loop_edges:
            context.increment_iteration(current_node)

        return None

    def _try_deterministic_routing(
        self,
        edges: List[Edge],
        eval_context: Dict[str, Any],
    ) -> Optional[RouteDecision]:
        """Try deterministic routing (single edge or unconditional edge)."""
        # Single edge = deterministic
        if len(edges) == 1:
            edge = edges[0]
            # Still check condition if present
            if edge.condition:
                result, err = self.evaluate_edge_condition(edge, eval_context)
                if not result:
                    return RouteDecision(
                        next_node_id=None,
                        decision_type=DecisionType.FLOW_COMPLETE,
                        reasoning=f"Single edge condition failed: {err}",
                        evaluated_conditions=[ConditionEval(
                            edge_id=edge.edge_id,
                            expression=str(edge.condition.expression or edge.condition.field),
                            result=False,
                            error=err,
                        )],
                    )

            return RouteDecision(
                next_node_id=edge.to_node,
                decision_type=DecisionType.DETERMINISTIC,
                reasoning=f"Single outgoing edge: {edge.edge_id}",
            )

        # Check for unconditional edges
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
        valid_edges = []
        evaluated = []

        # Sort edges by priority (higher first)
        sorted_edges = sorted(edges, key=lambda e: e.priority, reverse=True)

        for edge in sorted_edges:
            expression_str = ""
            if edge.condition:
                expression_str = edge.condition.expression or f"{edge.condition.field} {edge.condition.operator} {edge.condition.value}"

            result, err = self.evaluate_edge_condition(edge, eval_context)

            evaluated.append(ConditionEval(
                edge_id=edge.edge_id,
                expression=expression_str or "(unconditional)",
                result=result,
                error=err,
            ))

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

            # Determine confidence based on whether LLM was actually used
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

            # Fallback to default edge
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

        # Sort by priority (higher first), then by edge_id for determinism
        sorted_edges = sorted(
            edges,
            key=lambda e: (-e.priority, e.edge_id)
        )
        return sorted_edges[0]


# =============================================================================
# Convenience Functions
# =============================================================================


def create_router(
    llm_tiebreaker: Optional[Callable[[List[Edge], RouteContext], str]] = None,
) -> SmartRouter:
    """Create a SmartRouter with optional LLM tie-breaker.

    Args:
        llm_tiebreaker: Optional callable for LLM tie-breaking.

    Returns:
        Configured SmartRouter instance.
    """
    return SmartRouter(llm_tiebreaker=llm_tiebreaker)


def route_step(
    current_node: str,
    graph: FlowGraph,
    step_output: StepOutput,
    context: RouteContext,
    router: Optional[SmartRouter] = None,
) -> RouteDecision:
    """Convenience function for routing a step.

    Args:
        current_node: The current node ID.
        graph: The flow graph.
        step_output: The step output.
        context: The routing context.
        router: Optional router instance. If not provided, creates a new one.

    Returns:
        The routing decision.
    """
    if router is None:
        router = SmartRouter()

    return router.route(current_node, graph, step_output, context)
