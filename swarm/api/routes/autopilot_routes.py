"""
Autopilot endpoints for Flow Studio API.

Provides REST endpoints for:
- Starting autopilot runs
- Getting autopilot status
- Ticking autopilot forward
- Canceling/stopping/pausing/resuming autopilot runs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["autopilot"])


# =============================================================================
# Pydantic Models
# =============================================================================


class RunActionResponse(BaseModel):
    """Generic response for run actions."""

    run_id: str
    status: str
    message: str
    timestamp: str


class AutopilotStartRequest(BaseModel):
    """Request to start an autopilot run."""

    issue_ref: Optional[str] = Field(None, description="Issue reference (e.g., 'owner/repo#123')")
    flow_keys: Optional[List[str]] = Field(
        None, description="Specific flows to execute (defaults to all SDLC flows)"
    )
    profile_id: Optional[str] = Field(None, description="Profile ID to use")
    backend: str = Field("claude-step-orchestrator", description="Backend for execution")
    params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")
    auto_apply_wisdom: bool = Field(False, description="Auto-apply wisdom patches at run end")
    auto_apply_policy: str = Field("safe", description="Policy for auto-apply: 'safe' or 'all'")
    auto_apply_patch_types: Optional[List[str]] = Field(
        None,
        description="Patch types to auto-apply (defaults to ['flow_evolution', 'station_tuning'])",
    )


class AutopilotStartResponse(BaseModel):
    """Response when starting an autopilot run."""

    run_id: str
    status: str
    flows: List[str]
    events_url: str
    created_at: str


class WisdomApplyResultResponse(BaseModel):
    """Summary of wisdom auto-apply results."""

    patches_processed: int = 0
    patches_applied: int = 0
    patches_rejected: int = 0
    patches_skipped: int = 0
    applied_patch_ids: List[str] = Field(default_factory=list)


class AutopilotStatusResponse(BaseModel):
    """Response for autopilot status check."""

    run_id: str
    status: str
    current_flow: Optional[str] = None
    flows_completed: List[str]
    flows_failed: List[str]
    error: Optional[str] = None
    duration_ms: int = 0
    wisdom_apply_result: Optional[WisdomApplyResultResponse] = None


class AutopilotStopRequest(BaseModel):
    """Request to stop an autopilot run gracefully."""

    reason: str = Field("user_initiated", description="Reason for stopping")


# Global autopilot controller (initialized on first use)
_autopilot_controller = None


def _get_autopilot_controller():
    """Get or create the global autopilot controller."""
    global _autopilot_controller
    if _autopilot_controller is None:
        from swarm.runtime.autopilot import AutopilotController

        _autopilot_controller = AutopilotController()
    return _autopilot_controller


# =============================================================================
# Autopilot Endpoints
# =============================================================================


@router.post("", response_model=AutopilotStartResponse, status_code=201)
async def start_autopilot(request: AutopilotStartRequest):
    """Start an autopilot run for end-to-end SDLC execution.

    Creates a new run configured for autonomous execution. All flows are
    executed sequentially without mid-flow human intervention. PAUSE intents
    are automatically rewritten to DETOUR (clarifier sidequest).

    When auto_apply_wisdom is enabled, wisdom patches will be automatically
    applied at run completion using the specified policy:
    - 'safe': Only applies patches that pass schema validation, compile preview,
              and don't require human review.
    - 'all': Applies all valid patches regardless of review requirements.

    Args:
        request: Autopilot start request with optional issue_ref, flow configuration,
                 and auto-apply wisdom settings.

    Returns:
        AutopilotStartResponse with run_id and scheduled flows.
    """
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

    except Exception as e:
        logger.error("Failed to start autopilot run: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "autopilot_start_failed",
                "message": str(e),
                "details": {},
            },
        )


@router.get("/{run_id}", response_model=AutopilotStatusResponse)
async def get_autopilot_status(run_id: str):
    """Get the status of an autopilot run.

    Args:
        run_id: The autopilot run identifier.

    Returns:
        AutopilotStatusResponse with current status, progress, and wisdom apply results.
    """
    try:
        controller = _get_autopilot_controller()
        result = controller.get_result(run_id)

        # Convert wisdom apply result if present
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

    except Exception as e:
        logger.error("Failed to get autopilot status: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "autopilot_status_failed",
                "message": str(e),
                "details": {},
            },
        )


@router.post("/{run_id}/tick", response_model=AutopilotStatusResponse)
async def tick_autopilot(run_id: str):
    """Advance an autopilot run by one flow.

    Each tick executes one complete flow in the sequence. Call repeatedly
    until the run completes.

    Args:
        run_id: The autopilot run identifier.

    Returns:
        AutopilotStatusResponse with updated status and wisdom apply results.
    """
    try:
        controller = _get_autopilot_controller()
        controller.tick(run_id)
        result = controller.get_result(run_id)

        # Convert wisdom apply result if present
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

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "autopilot_not_found",
                "message": str(e),
                "details": {"run_id": run_id},
            },
        )
    except Exception as e:
        logger.error("Failed to tick autopilot: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "autopilot_tick_failed",
                "message": str(e),
                "details": {},
            },
        )


@router.delete("/{run_id}", response_model=RunActionResponse)
async def cancel_autopilot(run_id: str):
    """Cancel an autopilot run.

    Terminates the autopilot run and marks it as canceled.

    Args:
        run_id: The autopilot run identifier.

    Returns:
        Action response confirming cancellation.
    """
    try:
        controller = _get_autopilot_controller()
        canceled = controller.cancel(run_id)

        if not canceled:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": "Run is already complete or not found",
                    "details": {"run_id": run_id},
                },
            )

        return RunActionResponse(
            run_id=run_id,
            status="canceled",
            message="Autopilot run canceled successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel autopilot: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "autopilot_cancel_failed",
                "message": str(e),
                "details": {},
            },
        )


@router.post("/{run_id}/stop", response_model=RunActionResponse)
async def stop_autopilot(run_id: str, request: AutopilotStopRequest):
    """Stop an autopilot run gracefully with savepoint.

    Unlike cancel, stop creates a clean savepoint that can be resumed.
    The run will complete its current flow (if any) then stop.

    Args:
        run_id: The autopilot run identifier.
        request: Stop request with reason.

    Returns:
        Action response confirming stop initiation.
    """
    try:
        controller = _get_autopilot_controller()
        stopped = controller.stop(run_id, reason=request.reason)

        if not stopped:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": "Run is already complete or not found",
                    "details": {"run_id": run_id},
                },
            )

        return RunActionResponse(
            run_id=run_id,
            status="stopping",
            message=f"Autopilot run stopping: {request.reason}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to stop autopilot: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "autopilot_stop_failed",
                "message": str(e),
                "details": {},
            },
        )


@router.post("/{run_id}/pause", response_model=RunActionResponse)
async def pause_autopilot(run_id: str):
    """Pause an autopilot run at the next flow boundary.

    The run will complete its current flow (if any) then pause.
    Can be resumed later with the resume endpoint.

    Args:
        run_id: The autopilot run identifier.

    Returns:
        Action response confirming pause initiation.
    """
    try:
        controller = _get_autopilot_controller()
        paused = controller.pause(run_id)

        if not paused:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": "Run cannot be paused (already complete, paused, or not found)",
                    "details": {"run_id": run_id},
                },
            )

        return RunActionResponse(
            run_id=run_id,
            status="pausing",
            message="Autopilot run will pause after current flow completes",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to pause autopilot: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "autopilot_pause_failed",
                "message": str(e),
                "details": {},
            },
        )


@router.post("/{run_id}/resume", response_model=RunActionResponse)
async def resume_autopilot(run_id: str):
    """Resume a paused or stopped autopilot run.

    Continues execution from the saved flow index.

    Args:
        run_id: The autopilot run identifier.

    Returns:
        Action response confirming resume.
    """
    try:
        controller = _get_autopilot_controller()
        resumed = controller.resume(run_id)

        if not resumed:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": "Run cannot be resumed (not paused/stopped or not found)",
                    "details": {"run_id": run_id},
                },
            )

        return RunActionResponse(
            run_id=run_id,
            status="running",
            message="Autopilot run resumed successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to resume autopilot: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "autopilot_resume_failed",
                "message": str(e),
                "details": {},
            },
        )
