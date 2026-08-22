"""Pydantic models for run creation, control, and inspection endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunStartRequest(BaseModel):
    """Request to initialize one durable run record.

    For execute mode, ``backend`` records the requested executor. Dispatch
    happens at the executor boundary and is not part of this initialization
    endpoint.
    """

    flow_id: str = Field(..., description="Flow selected for the run")
    run_id: Optional[str] = Field(None, description="Custom run ID (generated if omitted)")
    context: Optional[Dict[str, Any]] = Field(None, description="Initial context for the run")
    start_step: Optional[str] = Field(None, description="Initial node (defaults to graph entry)")
    mode: str = Field("execute", description="Requested mode: execute, preview, validate")
    backend: str = Field(
        "claude-step-orchestrator",
        description="Requested execution backend; recorded here and dispatched at the executor boundary",
    )


class InjectRequest(BaseModel):
    step_id: str = Field(..., description="ID for the injected step")
    station_id: str = Field(..., description="Station to use for the step")
    position: str = Field(
        "next", description="Where to inject: next, after:<step_id>, before:<step_id>"
    )
    params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the step")


class InterruptRequest(BaseModel):
    detour_flow: Optional[str] = Field(None, description="Flow to execute as detour")
    detour_steps: Optional[List[str]] = Field(
        None, description="Specific steps to execute as detour"
    )
    reason: str = Field(..., description="Reason for the interrupt")
    resume_after: bool = Field(True, description="Resume the original graph after detour")


class PauseRequest(BaseModel):
    wait_for_step: bool = Field(
        True, description="Wait for the current step transaction before pausing"
    )


class ResumeRequest(BaseModel):
    from_step: Optional[str] = Field(None, description="Optional explicit resume node")


class StopRequest(BaseModel):
    reason: str = Field("user_initiated", description="Reason for stopping")
    drain_timeout_ms: int = Field(30000, description="Message-drain timeout in milliseconds")


class RunStartResponse(BaseModel):
    run_id: str
    flow_id: str
    status: str
    created_at: str
    events_url: str


class RunSummary(BaseModel):
    run_id: str
    flow_key: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None


class RunListResponse(BaseModel):
    runs: List[RunSummary]


class RunState(BaseModel):
    """Compatibility projection of the canonical runtime RunState."""

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
    run_id: str
    status: str
    message: str
    timestamp: str


class StopReportInfo(BaseModel):
    last_step_id: Optional[str] = None
    last_routing_intent: Optional[str] = None
    last_tool_calls: List[str] = Field(default_factory=list)
    open_assumptions: List[str] = Field(default_factory=list)
    stop_reason: str = ""
    stopped_at: str = ""


class StopResponse(BaseModel):
    run_id: str
    status: str
    message: str
    timestamp: str
    stop_report_path: Optional[str] = None
    stop_info: Optional[StopReportInfo] = None


class InterruptionFrameResponse(BaseModel):
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
    run_id: str
    stack_depth: int
    frames: List[InterruptionFrameResponse]
    detours: List[Dict[str, Any]] = Field(default_factory=list)
