"""API routes for durable multi-flow autopilot runs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from swarm.runtime.safe_paths import validate_path_component

logger = logging.getLogger(__name__)
router = APIRouter(tags=["autopilot"])


class RunActionResponse(BaseModel):
    run_id: str
    status: str
    message: str
    timestamp: str


class AutopilotStartRequest(BaseModel):
    issue_ref: Optional[str] = Field(None, description="Issue reference, for example owner/repo#123")
    flow_keys: Optional[List[str]] = Field(None, description="Flows to execute")
    profile_id: Optional[str] = None
    backend: str = "claude-step-orchestrator"
    params: Optional[Dict[str, Any]] = None
    auto_apply_wisdom: bool = False
    auto_apply_policy: str = "safe"
    auto_apply_patch_types: Optional[List[str]] = None


class AutopilotStartResponse(BaseModel):
    run_id: str
    status: str
    flows: List[str]
    events_url: str
    created_at: str


class WisdomApplyResultResponse(BaseModel):
    patches_processed: int = 0
    patches_applied: int = 0
    patches_rejected: int = 0
    patches_skipped: int = 0
    applied_patch_ids: List[str] = Field(default_factory=list)


class AutopilotStatusResponse(BaseModel):
    run_id: str
    status: str
    current_flow: Optional[str] = None
    flows_completed: List[str]
    flows_failed: List[str]
    error: Optional[str] = None
    duration_ms: int = 0
    wisdom_apply_result: Optional[WisdomApplyResultResponse] = None


class AutopilotStopRequest(BaseModel):
    reason: str = "user_initiated"


_autopilot_controller = None


def _get_autopilot_controller():
    """Return the API-facing controller that owns a canonical run identity."""
    global _autopilot_controller
    if _autopilot_controller is None:
        from swarm.runtime.canonical_autopilot import CanonicalAutopilotController

        _autopilot_controller = CanonicalAutopilotController()
    return _autopilot_controller


def _validate_run_id(run_id: str) -> None:
    try:
        validate_path_component(run_id, "run_id")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _status_response(controller, run_id: str) -> AutopilotStatusResponse:
    result = controller.get_result(run_id)
    wisdom_result = None
    if result.wisdom_apply_result:
        wisdom_result = WisdomApplyResultResponse(
            patches_processed=result.wisdom_apply_result.patches_processed,
            patches_applied=result.wisdom_apply_result.patches_applied,
            patches_rejected=result.wisdom_apply_result.patches_rejected,
            patches_skipped=result.wisdom_apply_result.patches_skipped,
            applied_patch_ids=result.wisdom_apply_result.applied_patch_ids,
        )
    return AutopilotStatusResponse(
        run_id=run_id,
        status=result.status.value,
        current_flow=result.current_flow,
        flows_completed=result.flows_completed,
        flows_failed=result.flows_failed,
        error=result.error,
        duration_ms=result.duration_ms,
        wisdom_apply_result=wisdom_result,
    )


@router.post("", response_model=AutopilotStartResponse, status_code=201)
async def start_autopilot(request: AutopilotStartRequest):
    try:
        controller = _get_autopilot_controller()
        run_id = controller.start(
            issue_ref=request.issue_ref,
            flow_keys=request.flow_keys,
            profile_id=request.profile_id,
            backend=request.backend,
            initiator="api",
            params=request.params,
            auto_apply_wisdom=request.auto_apply_wisdom,
            auto_apply_policy=request.auto_apply_policy,
            auto_apply_patch_types=request.auto_apply_patch_types,
        )
        result = controller.get_result(run_id)
        return AutopilotStartResponse(
            run_id=run_id,
            status=result.status.value,
            flows=request.flow_keys or controller._get_sdlc_flows(),
            events_url=f"/api/runs/{run_id}/events",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    except (FileExistsError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to start autopilot run")
        raise HTTPException(
            status_code=500,
            detail={"error": "autopilot_start_failed", "message": str(exc), "details": {}},
        ) from exc


@router.get("/{run_id}", response_model=AutopilotStatusResponse)
async def get_autopilot_status(run_id: str):
    _validate_run_id(run_id)
    return _status_response(_get_autopilot_controller(), run_id)


@router.post("/{run_id}/tick", response_model=AutopilotStatusResponse)
async def tick_autopilot(run_id: str):
    _validate_run_id(run_id)
    controller = _get_autopilot_controller()
    try:
        controller.tick(run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "autopilot_not_found", "message": str(exc), "details": {"run_id": run_id}},
        ) from exc
    except Exception as exc:
        logger.exception("Failed to tick autopilot run %s", run_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "autopilot_tick_failed", "message": str(exc), "details": {}},
        ) from exc
    return _status_response(controller, run_id)


@router.delete("/{run_id}", response_model=RunActionResponse)
async def cancel_autopilot(run_id: str):
    _validate_run_id(run_id)
    controller = _get_autopilot_controller()
    if not controller.cancel(run_id):
        raise HTTPException(
            status_code=409,
            detail={"error": "invalid_state", "message": "Run is complete or unknown", "details": {"run_id": run_id}},
        )
    return RunActionResponse(
        run_id=run_id,
        status="canceled",
        message="Autopilot run canceled successfully",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/{run_id}/stop", response_model=RunActionResponse)
async def stop_autopilot(run_id: str, request: AutopilotStopRequest):
    _validate_run_id(run_id)
    controller = _get_autopilot_controller()
    if not controller.stop(run_id, reason=request.reason):
        raise HTTPException(
            status_code=409,
            detail={"error": "invalid_state", "message": "Run cannot be stopped", "details": {"run_id": run_id}},
        )
    return RunActionResponse(
        run_id=run_id,
        status="stopping",
        message=f"Autopilot run stopping: {request.reason}",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/{run_id}/pause", response_model=RunActionResponse)
async def pause_autopilot(run_id: str):
    _validate_run_id(run_id)
    controller = _get_autopilot_controller()
    if not controller.pause(run_id):
        raise HTTPException(
            status_code=409,
            detail={"error": "invalid_state", "message": "Run cannot be paused", "details": {"run_id": run_id}},
        )
    return RunActionResponse(
        run_id=run_id,
        status="pausing",
        message="Autopilot run will pause after the current flow",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/{run_id}/resume", response_model=RunActionResponse)
async def resume_autopilot(run_id: str):
    _validate_run_id(run_id)
    controller = _get_autopilot_controller()
    if not controller.resume(run_id):
        raise HTTPException(
            status_code=409,
            detail={"error": "invalid_state", "message": "Run cannot be resumed", "details": {"run_id": run_id}},
        )
    return RunActionResponse(
        run_id=run_id,
        status="running",
        message="Autopilot run resumed successfully",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
