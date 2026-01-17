"""Shared routing types and interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class DecisionType(str, Enum):
    """Type of routing decision made."""

    EXPLICIT = "explicit"
    EXIT_CONDITION = "exit_condition"
    DETERMINISTIC = "deterministic"
    CEL = "cel"
    LLM_TIEBREAKER = "llm_tiebreaker"
    FLOW_COMPLETE = "flow_complete"
    ERROR = "error"


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
    """The result of a routing decision."""

    next_node_id: Optional[str]
    decision_type: DecisionType
    reasoning: str
    evaluated_conditions: List[ConditionEval] = field(default_factory=list)
    confidence: float = 1.0
    needs_human: bool = False
    loop_count: int = 0


@dataclass
class StepOutput:
    """Output from a step execution relevant to routing."""

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
    """Context for routing decisions."""

    run_id: str
    flow_key: str
    iteration_counts: Dict[str, int] = field(default_factory=dict)
    max_iterations_default: int = 50
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


@dataclass
class EdgeCondition:
    """Condition for edge traversal."""

    field: Optional[str] = None
    operator: str = "equals"
    value: Any = None
    expression: Optional[str] = None


@dataclass
class Edge:
    """An edge in the flow graph."""

    edge_id: str
    from_node: str
    to_node: str
    condition: Optional[EdgeCondition] = None
    priority: int = 50
    edge_type: str = "sequence"

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
    exit_on: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeConfig":
        """Create a NodeConfig from a dictionary."""
        params = data.get("params", {})
        overrides = data.get("overrides", {})

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
    """A flow graph for routing decisions."""

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
        return self.policy.get("max_loop_iterations", 50)

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


@dataclass
class RoutingResult:
    """Result of a routing decision with full audit trail."""

    edge: Optional[Edge] = None
    method: str = "deterministic"
    terminate: bool = False
    needs_human: bool = False
    explanation: Optional[Dict[str, Any]] = None


@dataclass
class RunContext:
    """Context for routing decisions during flow execution."""

    run_id: str
    flow_key: str
    step_output: Dict[str, Any]
    iteration_counts: Dict[str, int] = field(default_factory=dict)
    max_iterations: int = 50
    annotations: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from step output or annotations."""
        if key in self.step_output:
            return self.step_output[key]
        return self.annotations.get(key, default)


@dataclass
class StepOutputData:
    """Normalized step output for routing decisions."""

    status: str = "UNKNOWN"
    can_further_iteration_help: Optional[bool] = None
    next_step_id: Optional[str] = None
    proposed_action: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepOutputData":
        """Create StepOutputData from a dictionary (handoff data)."""
        can_help = data.get("can_further_iteration_help")
        if isinstance(can_help, str):
            can_help = can_help.lower() in ("yes", "true", "1")

        return cls(
            status=data.get("status", "UNKNOWN"),
            can_further_iteration_help=can_help,
            next_step_id=data.get("next_step_id"),
            proposed_action=data.get("proposed_action"),
            custom_fields={
                k: v
                for k, v in data.items()
                if k
                not in ("status", "can_further_iteration_help", "next_step_id", "proposed_action")
            },
        )


@dataclass
class RoutingContext:
    """Context for routing decisions during flow execution."""

    run_id: str
    flow_key: str
    current_node: str
    iteration_counts: Dict[str, int] = field(default_factory=dict)
    max_iterations: int = 50
    annotations: Dict[str, Any] = field(default_factory=dict)
