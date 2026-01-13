"""Session result types for the Claude SDK integration.

This module provides dataclasses for results from the Work -> Finalize -> Route
phases of a step session.

These are SDK-free modules (no SDK calls involved).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from swarm.runtime.types.tool_call import NormalizedToolCall

from .telemetry import TelemetryData


@dataclass
class WorkPhaseResult:
    """Result from the work phase of a step session.

    Attributes:
        success: Whether the work phase completed successfully.
        output: Concatenated assistant text output.
        events: List of raw SDK events captured during work.
        token_counts: Token usage statistics.
        model: Model name used.
        error: Error message if work phase failed.
        tool_calls: List of NormalizedToolCall instances made during work.
    """

    success: bool
    output: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    token_counts: Dict[str, int] = field(
        default_factory=lambda: {"prompt": 0, "completion": 0, "total": 0}
    )
    model: str = "unknown"
    error: Optional[str] = None
    tool_calls: List[NormalizedToolCall] = field(default_factory=list)


@dataclass
class FinalizePhaseResult:
    """Result from the finalize phase of a step session.

    Attributes:
        envelope: Parsed handoff envelope data.
        raw_output: Raw structured output from SDK.
        success: Whether finalization succeeded.
        error: Error message if finalization failed.
    """

    envelope: Optional[Dict[str, Any]] = None
    raw_output: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class RoutePhaseResult:
    """Result from the route phase of a step session.

    Attributes:
        signal: Parsed routing signal data.
        raw_output: Raw structured output from SDK.
        success: Whether routing succeeded.
        error: Error message if routing failed.
    """

    signal: Optional[Dict[str, Any]] = None
    raw_output: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class StepSessionResult:
    """Combined result from all phases of a step session.

    Attributes:
        work: Result from work phase.
        finalize: Result from finalize phase (may be None if inline).
        route: Result from route phase (may be None if terminal).
        duration_ms: Total session duration in milliseconds.
        session_id: Unique session identifier.
        telemetry: Telemetry data for each phase.
    """

    work: WorkPhaseResult
    finalize: Optional[FinalizePhaseResult] = None
    route: Optional[RoutePhaseResult] = None
    duration_ms: int = 0
    session_id: str = ""
    telemetry: Dict[str, TelemetryData] = field(default_factory=dict)
