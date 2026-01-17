from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RunStats:
    """Aggregated statistics for a run."""

    run_id: str
    flow_keys: List[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_steps: int
    completed_steps: int
    total_tokens: int
    total_duration_ms: int
    tool_call_count: int = 0
    file_change_count: int = 0


@dataclass
class StepStats:
    """Statistics for a single step."""

    step_id: str
    flow_key: str
    agent_key: Optional[str]
    status: str
    duration_ms: int
    total_tokens: int
    handoff_status: Optional[str]
    routing_decision: Optional[str]
    tool_calls: int = 0


@dataclass
class ToolBreakdown:
    """Breakdown of tool usage."""

    tool_name: str
    call_count: int
    total_duration_ms: int
    success_rate: float
    avg_duration_ms: float


@dataclass
class Fact:
    """A structured fact extracted from agent output (inventory marker).

    Facts represent requirements, solutions, traces, assumptions, and decisions
    extracted from agent outputs using REQ_*, SOL_*, TRC_*, ASM_*, DEC_* markers.
    """

    fact_id: str
    run_id: str
    step_id: str
    flow_key: str
    agent_key: Optional[str]
    marker_type: str  # REQ, SOL, TRC, ASM, DEC
    marker_id: str  # e.g., REQ_001
    fact_type: str  # requirement, solution, trace, assumption, decision
    content: str
    priority: Optional[str] = None  # MUST, SHOULD, NICE_TO_HAVE
    status: Optional[str] = None  # verified, unverified, deprecated
    evidence: Optional[str] = None
    created_at: Optional[datetime] = None
    extracted_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class RoutingDecisionRecord:
    """A routing decision record for UI queries.

    Captures the routing decision made after each step execution,
    including the method used, candidates evaluated, and the chosen path.
    """

    run_id: str
    step_seq: int
    flow_id: str
    station_id: str
    routing_mode: Optional[str]  # deterministic, llm_tiebreak, etc.
    routing_source: Optional[str]  # navigator/fast_path/deterministic_fallback
    chosen_candidate_id: Optional[str]  # Selected edge ID
    candidate_count: int
    decision: str  # advance/loop/repeat/detour/terminate/escalate
    target_node: Optional[str]  # Next node to execute
    timestamp: datetime
    terminate: bool = False
    needs_human: bool = False
    explanation: Optional[Dict[str, Any]] = None
