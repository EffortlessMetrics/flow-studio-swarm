"""Run state and handoff envelope types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ._time import _datetime_to_iso, _iso_to_datetime
from .audit import (
    AssumptionEntry,
    DecisionLogEntry,
    ObservationEntry,
    StationOpinion,
    assumption_entry_from_dict,
    assumption_entry_to_dict,
    decision_log_entry_from_dict,
    decision_log_entry_to_dict,
)
from .routing import (
    RoutingSignal,
    routing_explanation_to_dict,
    routing_signal_from_dict,
    routing_signal_to_dict,
)


@dataclass
class HandoffEnvelope:
    """Durable per-step handoff artifact for cross-step communication."""

    step_id: str
    flow_key: str
    run_id: str
    routing_signal: RoutingSignal
    summary: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    file_changes: Dict[str, Any] = field(default_factory=dict)
    status: str = "succeeded"
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    station_id: Optional[str] = None
    station_version: Optional[int] = None
    prompt_hash: Optional[str] = None
    verification_passed: bool = True
    verification_details: Dict[str, Any] = field(default_factory=dict)
    routing_audit: Optional[Dict[str, Any]] = None
    assumptions_made: List[AssumptionEntry] = field(default_factory=list)
    decisions_made: List[DecisionLogEntry] = field(default_factory=list)
    observations: List[ObservationEntry] = field(default_factory=list)
    station_opinions: List[StationOpinion] = field(default_factory=list)


def handoff_envelope_to_dict(envelope: HandoffEnvelope) -> Dict[str, Any]:
    """Convert HandoffEnvelope to a dictionary for serialization."""
    result = {
        "step_id": envelope.step_id,
        "flow_key": envelope.flow_key,
        "run_id": envelope.run_id,
        "routing_signal": routing_signal_to_dict(envelope.routing_signal),
        "summary": envelope.summary,
        "artifacts": dict(envelope.artifacts),
        "file_changes": dict(envelope.file_changes),
        "status": envelope.status,
        "error": envelope.error,
        "duration_ms": envelope.duration_ms,
        "timestamp": _datetime_to_iso(envelope.timestamp),
        "station_id": envelope.station_id,
        "station_version": envelope.station_version,
        "prompt_hash": envelope.prompt_hash,
        "verification_passed": envelope.verification_passed,
        "verification_details": dict(envelope.verification_details),
    }

    if envelope.routing_signal.explanation:
        result["routing_audit"] = routing_explanation_to_dict(envelope.routing_signal.explanation)
    elif envelope.routing_audit:
        result["routing_audit"] = envelope.routing_audit

    if envelope.assumptions_made:
        result["assumptions_made"] = [
            assumption_entry_to_dict(a) for a in envelope.assumptions_made
        ]
    if envelope.decisions_made:
        result["decisions_made"] = [decision_log_entry_to_dict(d) for d in envelope.decisions_made]

    if envelope.station_opinions:
        result["station_opinions"] = list(envelope.station_opinions)

    return result


def handoff_envelope_from_dict(data: Dict[str, Any]) -> HandoffEnvelope:
    """Parse HandoffEnvelope from a dictionary."""
    routing_signal_data = data.get("routing_signal", {})
    routing_signal = routing_signal_from_dict(routing_signal_data)

    routing_audit = data.get("routing_audit")

    assumptions_made = [assumption_entry_from_dict(a) for a in data.get("assumptions_made", [])]
    decisions_made = [decision_log_entry_from_dict(d) for d in data.get("decisions_made", [])]

    station_opinions: List[StationOpinion] = list(data.get("station_opinions", []))

    return HandoffEnvelope(
        step_id=data.get("step_id", ""),
        flow_key=data.get("flow_key", ""),
        run_id=data.get("run_id", ""),
        routing_signal=routing_signal,
        summary=data.get("summary", ""),
        artifacts=dict(data.get("artifacts", {})),
        file_changes=dict(data.get("file_changes", {})),
        status=data.get("status", "succeeded"),
        error=data.get("error"),
        duration_ms=data.get("duration_ms", 0),
        timestamp=_iso_to_datetime(data.get("timestamp")) or datetime.now(timezone.utc),
        station_id=data.get("station_id"),
        station_version=data.get("station_version"),
        prompt_hash=data.get("prompt_hash"),
        verification_passed=data.get("verification_passed", True),
        verification_details=dict(data.get("verification_details", {})),
        routing_audit=routing_audit,
        assumptions_made=assumptions_made,
        decisions_made=decisions_made,
        station_opinions=station_opinions,
    )


@dataclass
class InterruptionFrame:
    """Frame representing an interruption point in the execution stack."""

    reason: str
    interrupted_at: datetime
    return_node: str
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    current_step_index: int = 0
    total_steps: int = 1
    sidequest_id: Optional[str] = None


@dataclass
class ResumePoint:
    """A saved resume point for continuation after interruption."""

    node_id: str
    saved_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InjectedNode:
    """Specification for a dynamically injected node."""

    node_id: str
    agent_key: str
    role: str = ""
    insert_after: Optional[str] = None
    insert_before: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    routing_override: Optional[Dict[str, Any]] = None


@dataclass
class InjectedNodeSpec:
    """Full execution specification for a dynamically injected node."""

    node_id: str
    station_id: str
    template_id: Optional[str] = None
    agent_key: Optional[str] = None
    role: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    sidequest_origin: Optional[str] = None
    sequence_index: int = 0
    total_in_sequence: int = 1


@dataclass
class RunState:
    """Durable program counter for stepwise flow execution with detour support."""

    run_id: str
    flow_key: str
    current_step_id: Optional[str] = None
    step_index: int = 0
    loop_state: Dict[str, int] = field(default_factory=dict)
    handoff_envelopes: Dict[str, HandoffEnvelope] = field(default_factory=dict)
    status: str = "pending"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_flow_index: int = 1
    flow_transition_history: List[Dict[str, Any]] = field(default_factory=list)
    interruption_stack: List[InterruptionFrame] = field(default_factory=list)
    resume_stack: List[ResumePoint] = field(default_factory=list)
    injected_nodes: List[str] = field(default_factory=list)
    injected_node_specs: Dict[str, InjectedNodeSpec] = field(default_factory=dict)
    completed_nodes: List[str] = field(default_factory=list)

    def push_interruption(
        self,
        reason: str,
        return_node: str,
        context_snapshot: Optional[Dict[str, Any]] = None,
        current_step_index: int = 0,
        total_steps: int = 1,
        sidequest_id: Optional[str] = None,
    ) -> None:
        """Push an interruption frame onto the stack."""
        frame = InterruptionFrame(
            reason=reason,
            interrupted_at=datetime.now(timezone.utc),
            return_node=return_node,
            context_snapshot=context_snapshot or {},
            current_step_index=current_step_index,
            total_steps=total_steps,
            sidequest_id=sidequest_id,
        )
        self.interruption_stack.append(frame)
        self.timestamp = datetime.now(timezone.utc)

    def pop_interruption(self) -> Optional[InterruptionFrame]:
        """Pop the most recent interruption frame from the stack."""
        if not self.interruption_stack:
            return None
        frame = self.interruption_stack.pop()
        self.timestamp = datetime.now(timezone.utc)
        return frame

    def peek_interruption(self) -> Optional[InterruptionFrame]:
        """Peek at the top of the interruption stack without popping."""
        if not self.interruption_stack:
            return None
        return self.interruption_stack[-1]

    def push_resume(
        self,
        node_id: str,
        saved_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Push a resume point onto the stack."""
        point = ResumePoint(
            node_id=node_id,
            saved_context=saved_context or {},
        )
        self.resume_stack.append(point)
        self.timestamp = datetime.now(timezone.utc)

    def pop_resume(self) -> Optional[ResumePoint]:
        """Pop the most recent resume point from the stack."""
        if not self.resume_stack:
            return None
        point = self.resume_stack.pop()
        self.timestamp = datetime.now(timezone.utc)
        return point

    def peek_resume(self) -> Optional[ResumePoint]:
        """Peek at the top of the resume stack without popping."""
        if not self.resume_stack:
            return None
        return self.resume_stack[-1]

    def add_injected_node(self, node_id: str) -> None:
        """Add a dynamically injected node ID to the list."""
        if node_id not in self.injected_nodes:
            self.injected_nodes.append(node_id)
            self.timestamp = datetime.now(timezone.utc)

    def register_injected_node(self, spec: InjectedNodeSpec) -> None:
        """Register an injected node with its full execution spec."""
        self.injected_node_specs[spec.node_id] = spec
        if spec.node_id not in self.injected_nodes:
            self.injected_nodes.append(spec.node_id)
        self.timestamp = datetime.now(timezone.utc)

    def get_injected_node_spec(self, node_id: str) -> Optional[InjectedNodeSpec]:
        """Get the execution spec for an injected node."""
        return self.injected_node_specs.get(node_id)

    def mark_node_completed(self, node_id: str) -> None:
        """Mark a node as completed."""
        if node_id not in self.completed_nodes:
            self.completed_nodes.append(node_id)
            self.timestamp = datetime.now(timezone.utc)

    def is_node_completed(self, node_id: str) -> bool:
        """Check if a node has been completed."""
        return node_id in self.completed_nodes

    def is_interrupted(self) -> bool:
        """Check if the run is currently in an interrupted state."""
        return len(self.interruption_stack) > 0

    def get_interruption_depth(self) -> int:
        """Get the current depth of nested interruptions."""
        return len(self.interruption_stack)


def interruption_frame_to_dict(frame: InterruptionFrame) -> Dict[str, Any]:
    """Convert InterruptionFrame to a dictionary for serialization."""
    return {
        "reason": frame.reason,
        "interrupted_at": _datetime_to_iso(frame.interrupted_at),
        "return_node": frame.return_node,
        "context_snapshot": dict(frame.context_snapshot),
        "current_step_index": frame.current_step_index,
        "total_steps": frame.total_steps,
        "sidequest_id": frame.sidequest_id,
    }


def interruption_frame_from_dict(data: Dict[str, Any]) -> InterruptionFrame:
    """Parse InterruptionFrame from a dictionary."""
    return InterruptionFrame(
        reason=data.get("reason", ""),
        interrupted_at=_iso_to_datetime(data.get("interrupted_at")) or datetime.now(timezone.utc),
        return_node=data.get("return_node", ""),
        context_snapshot=dict(data.get("context_snapshot", {})),
        current_step_index=data.get("current_step_index", 0),
        total_steps=data.get("total_steps", 1),
        sidequest_id=data.get("sidequest_id"),
    )


def resume_point_to_dict(point: ResumePoint) -> Dict[str, Any]:
    """Convert ResumePoint to a dictionary for serialization."""
    return {
        "node_id": point.node_id,
        "saved_context": dict(point.saved_context),
    }


def resume_point_from_dict(data: Dict[str, Any]) -> ResumePoint:
    """Parse ResumePoint from a dictionary."""
    return ResumePoint(
        node_id=data.get("node_id", ""),
        saved_context=dict(data.get("saved_context", {})),
    )


def injected_node_to_dict(node: InjectedNode) -> Dict[str, Any]:
    """Convert InjectedNode to a dictionary for serialization."""
    return {
        "node_id": node.node_id,
        "agent_key": node.agent_key,
        "role": node.role,
        "insert_after": node.insert_after,
        "insert_before": node.insert_before,
        "params": dict(node.params),
        "routing_override": node.routing_override,
    }


def injected_node_from_dict(data: Dict[str, Any]) -> InjectedNode:
    """Parse InjectedNode from a dictionary."""
    return InjectedNode(
        node_id=data.get("node_id", ""),
        agent_key=data.get("agent_key", ""),
        role=data.get("role", ""),
        insert_after=data.get("insert_after"),
        insert_before=data.get("insert_before"),
        params=dict(data.get("params", {})),
        routing_override=data.get("routing_override"),
    )


def injected_node_spec_to_dict(spec: InjectedNodeSpec) -> Dict[str, Any]:
    """Convert InjectedNodeSpec to dictionary for serialization."""
    return {
        "node_id": spec.node_id,
        "station_id": spec.station_id,
        "template_id": spec.template_id,
        "agent_key": spec.agent_key,
        "role": spec.role,
        "params": dict(spec.params),
        "sidequest_origin": spec.sidequest_origin,
        "sequence_index": spec.sequence_index,
        "total_in_sequence": spec.total_in_sequence,
    }


def injected_node_spec_from_dict(data: Dict[str, Any]) -> InjectedNodeSpec:
    """Parse InjectedNodeSpec from dictionary."""
    return InjectedNodeSpec(
        node_id=data.get("node_id", ""),
        station_id=data.get("station_id", ""),
        template_id=data.get("template_id"),
        agent_key=data.get("agent_key"),
        role=data.get("role", ""),
        params=dict(data.get("params", {})),
        sidequest_origin=data.get("sidequest_origin"),
        sequence_index=data.get("sequence_index", 0),
        total_in_sequence=data.get("total_in_sequence", 1),
    )


def run_state_to_dict(state: RunState) -> Dict[str, Any]:
    """Convert RunState to a dictionary for serialization."""
    return {
        "run_id": state.run_id,
        "flow_key": state.flow_key,
        "flow_id": state.flow_key,
        "current_step_id": state.current_step_id,
        "current_node": state.current_step_id,
        "step_index": state.step_index,
        "loop_state": dict(state.loop_state),
        "handoff_envelopes": {
            step_id: handoff_envelope_to_dict(env)
            for step_id, env in state.handoff_envelopes.items()
        },
        "status": state.status,
        "timestamp": _datetime_to_iso(state.timestamp),
        "current_flow_index": state.current_flow_index,
        "flow_transition_history": list(state.flow_transition_history),
        "interruption_stack": [
            interruption_frame_to_dict(frame) for frame in state.interruption_stack
        ],
        "resume_stack": [resume_point_to_dict(point) for point in state.resume_stack],
        "injected_nodes": list(state.injected_nodes),
        "injected_node_specs": {
            node_id: injected_node_spec_to_dict(spec)
            for node_id, spec in state.injected_node_specs.items()
        },
        "completed_nodes": list(state.completed_nodes),
        "artifacts": {
            step_id: env.artifacts if hasattr(env, "artifacts") else {}
            for step_id, env in state.handoff_envelopes.items()
        },
    }


def run_state_from_dict(data: Dict[str, Any]) -> RunState:
    """Parse RunState from a dictionary."""
    envelopes_data = data.get("handoff_envelopes", {})
    handoff_envelopes = {
        step_id: handoff_envelope_from_dict(env_data)
        for step_id, env_data in envelopes_data.items()
    }

    interruption_stack_data = data.get("interruption_stack", [])
    interruption_stack = [
        interruption_frame_from_dict(frame_data) for frame_data in interruption_stack_data
    ]

    resume_stack_data = data.get("resume_stack", [])
    resume_stack = [resume_point_from_dict(point_data) for point_data in resume_stack_data]

    injected_node_specs_data = data.get("injected_node_specs", {})
    injected_node_specs = {
        node_id: injected_node_spec_from_dict(spec_data)
        for node_id, spec_data in injected_node_specs_data.items()
    }

    flow_key = data.get("flow_key") or data.get("flow_id", "")
    current_step_id = data.get("current_step_id") or data.get("current_node")

    return RunState(
        run_id=data.get("run_id", ""),
        flow_key=flow_key,
        current_step_id=current_step_id,
        step_index=data.get("step_index", 0),
        loop_state=dict(data.get("loop_state", {})),
        handoff_envelopes=handoff_envelopes,
        status=data.get("status", "pending"),
        timestamp=_iso_to_datetime(data.get("timestamp")) or datetime.now(timezone.utc),
        current_flow_index=data.get("current_flow_index", 1),
        flow_transition_history=list(data.get("flow_transition_history", [])),
        interruption_stack=interruption_stack,
        resume_stack=resume_stack,
        injected_nodes=list(data.get("injected_nodes", [])),
        injected_node_specs=injected_node_specs,
        completed_nodes=list(data.get("completed_nodes", [])),
    )
