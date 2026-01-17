"""
Pydantic models for run control endpoints.

Shared models used across runs_crud, runs_control, and runs_stack modules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Request Models
# =============================================================================


class RunStartRequest(BaseModel):
    """Request to start a new run."""

    flow_id: str = Field(..., description="Flow to execute")
    run_id: Optional[str] = Field(None, description="Custom run ID (generated if not provided)")
    context: Optional[Dict[str, Any]] = Field(None, description="Initial context for the run")
    start_step: Optional[str] = Field(None, description="Step to start from (defaults to first)")
    mode: str = Field("execute", description="Execution mode: execute, preview, validate")


class InjectRequest(BaseModel):
    """Request to inject a node into a run."""

    step_id: str = Field(..., description="ID for the injected step")
    station_id: str = Field(..., description="Station to use for the step")
    position: str = Field(
        "next", description="Where to inject: next, after:<step_id>, before:<step_id>"
    )
    params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the step")


class InterruptRequest(BaseModel):
    """Request to interrupt a run with a detour."""

    detour_flow: Optional[str] = Field(None, description="Flow to execute as detour")
    detour_steps: Optional[List[str]] = Field(
        None, description="Specific steps to execute as detour"
    )
    reason: str = Field(..., description="Reason for the interrupt")
    resume_after: bool = Field(True, description="Whether to resume original flow after detour")


class PauseRequest(BaseModel):
    """Request to pause a run."""

    wait_for_step: bool = Field(
        True, description="Wait for current step to complete before pausing"
    )


class ResumeRequest(BaseModel):
    """Request to resume a paused or stopped run."""

    from_step: Optional[str] = Field(None, description="Step to resume from (defaults to saved PC)")


class StopRequest(BaseModel):
    """Request to stop a run gracefully."""

    reason: str = Field("user_initiated", description="Reason for stopping")
    drain_timeout_ms: int = Field(30000, description="Timeout for draining messages in ms")


# =============================================================================
# Response Models
# =============================================================================


class RunStartResponse(BaseModel):
    """Response when starting a new run."""

    run_id: str
    flow_id: str
    status: str
    created_at: str
    events_url: str


class RunSummary(BaseModel):
    """Run summary for list endpoint."""

    run_id: str
    flow_key: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None


class RunListResponse(BaseModel):
    """Response for list runs endpoint."""

    runs: List[RunSummary]


class RunState(BaseModel):
    """Full run state."""

    run_id: str
    flow_id: str
    status: str
    current_step: Optional[str] = None
    completed_steps: List[str] = Field(default_factory=list)
    pending_steps: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    paused_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class RunActionResponse(BaseModel):
    """Generic response for run actions."""

    run_id: str
    status: str
    message: str
    timestamp: str


class StopReportInfo(BaseModel):
    """Information included in stop report."""

    last_step_id: Optional[str] = None
    last_routing_intent: Optional[str] = None
    last_tool_calls: List[str] = Field(default_factory=list)
    open_assumptions: List[str] = Field(default_factory=list)
    stop_reason: str = ""
    stopped_at: str = ""


class StopResponse(BaseModel):
    """Response when stopping a run."""

    run_id: str
    status: str
    message: str
    timestamp: str
    stop_report_path: Optional[str] = None
    stop_info: Optional[StopReportInfo] = None


class InterruptionFrameResponse(BaseModel):
    """A single frame in the interruption stack."""

    frame_id: str
    interrupted_flow: Optional[str] = None
    interrupted_step: Optional[str] = None
    injected_flow: Optional[str] = None
    reason: str
    started_at: str
    return_node: str
    current_step_index: int = 0
    total_steps: int = 1
    sidequest_id: Optional[str] = None


class InterruptionStackResponse(BaseModel):
    """Response for the interruption stack endpoint."""

    run_id: str
    stack_depth: int
    frames: List[InterruptionFrameResponse]
    detours: List[Dict[str, Any]] = Field(default_factory=list)
