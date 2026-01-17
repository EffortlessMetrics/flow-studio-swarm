"""
Run control endpoints for Flow Studio API.

Provides REST endpoints for:
- Pausing runs (POST /{run_id}/pause)
- Resuming runs (POST /{run_id}/resume)
- Injecting nodes (POST /{run_id}/inject)
- Interrupting runs (POST /{run_id}/interrupt)
- Canceling runs (DELETE /{run_id})
- Stopping runs gracefully (POST /{run_id}/stop)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException

from ..services.run_state import get_state_manager
from .runs_models import (
    InjectRequest,
    InterruptRequest,
    PauseRequest,
    ResumeRequest,
    RunActionResponse,
    StopReportInfo,
    StopRequest,
    StopResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


@router.post("/{run_id}/pause", response_model=RunActionResponse)
async def pause_run(
    run_id: str,
    request: Optional[PauseRequest] = None,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Pause a running run.

    Pauses execution at a clean boundary. The run can be resumed later.

    Pause semantics:
    - If wait_for_step=True (default): Sets status to "pausing" and waits for
      the current step to complete, then transitions to "paused".
    - If wait_for_step=False: Immediately sets status to "paused" (may interrupt
      current step mid-execution).

    Unlike stop, pause is temporary and the run resumes from the exact same
    program counter (PC). Stop creates a permanent savepoint with a report.

    Args:
        run_id: Run identifier.
        request: Optional pause request with wait_for_step flag.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response with new status.

    Raises:
        404: Run not found.
        409: Run is not in a pausable state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    # Default request if not provided
    if request is None:
        request = PauseRequest()

    try:
        state, _ = await state_manager.get_run(run_id)

        if state["status"] not in ("pending", "running"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot pause run with status '{state['status']}'",
                    "details": {"current_status": state["status"]},
                },
            )

        now = datetime.now(timezone.utc).isoformat()

        # Set appropriate pause status based on wait_for_step
        if request.wait_for_step:
            # Set to "pausing" - kernel will transition to "paused" after step completes
            new_status = "pausing"
        else:
            # Immediate pause
            new_status = "paused"

        await state_manager.update_run(
            run_id,
            {"status": new_status, "paused_at": now},
            expected_etag=expected_etag,
        )

        message = (
            "Run pausing (will pause after current step completes)"
            if request.wait_for_step
            else "Run paused immediately"
        )

        return RunActionResponse(
            run_id=run_id,
            status=new_status,
            message=message,
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.post("/{run_id}/resume", response_model=RunActionResponse)
async def resume_run(
    run_id: str,
    request: Optional[ResumeRequest] = None,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Resume a paused or stopped run.

    Resumes execution from the saved program counter (PC) or from a
    specified step.

    Resume can be called on runs with status:
    - "paused": Normal resume from pause point
    - "stopped": Resume from savepoint
    - "pausing": Cancel the pause and continue

    Args:
        run_id: Run identifier.
        request: Optional resume request with from_step override.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response with new status.

    Raises:
        404: Run not found.
        409: Run is not in a resumable state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    if request is None:
        request = ResumeRequest()

    try:
        state, _ = await state_manager.get_run(run_id)

        resumable_states = ("paused", "stopped", "pausing")
        if state["status"] not in resumable_states:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot resume run with status '{state['status']}'",
                    "details": {
                        "current_status": state["status"],
                        "resumable_states": list(resumable_states),
                    },
                },
            )

        now = datetime.now(timezone.utc).isoformat()

        # Build update payload
        update: Dict[str, Any] = {"status": "running", "updated_at": now}

        # If from_step is specified, update current_step
        if request.from_step:
            update["current_step"] = request.from_step

        # Clear pause/stop timestamps
        if state.get("paused_at"):
            update["paused_at"] = None
        if state.get("stopped_at"):
            update["stopped_at"] = None

        await state_manager.update_run(
            run_id,
            update,
            expected_etag=expected_etag,
        )

        from_info = f" from step '{request.from_step}'" if request.from_step else ""
        return RunActionResponse(
            run_id=run_id,
            status="running",
            message=f"Run resumed{from_info}",
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.post("/{run_id}/inject", response_model=RunActionResponse)
async def inject_node(
    run_id: str,
    request: InjectRequest,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Inject a node into a run.

    Inserts a new step into the run's execution plan. The step will be
    executed at the specified position.

    Args:
        run_id: Run identifier.
        request: Inject request with step details.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response confirming injection.

    Raises:
        404: Run not found.
        409: Run is not in an injectable state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    try:
        state, _ = await state_manager.get_run(run_id)

        if state["status"] not in ("pending", "running", "paused"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot inject into run with status '{state['status']}'",
                    "details": {"current_status": state["status"]},
                },
            )

        # Add injected step to pending steps
        pending = state.get("pending_steps", [])

        if request.position == "next":
            # Insert at beginning of pending
            pending.insert(0, request.step_id)
        elif request.position.startswith("after:"):
            target = request.position[6:]
            try:
                idx = pending.index(target) + 1
                pending.insert(idx, request.step_id)
            except ValueError:
                # Target not in pending, insert at end
                pending.append(request.step_id)
        elif request.position.startswith("before:"):
            target = request.position[7:]
            try:
                idx = pending.index(target)
                pending.insert(idx, request.step_id)
            except ValueError:
                # Target not in pending, insert at beginning
                pending.insert(0, request.step_id)
        else:
            pending.append(request.step_id)

        # Store injection metadata
        injections = state.get("context", {}).get("injections", [])
        injections.append(
            {
                "step_id": request.step_id,
                "station_id": request.station_id,
                "position": request.position,
                "params": request.params,
                "injected_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        now = datetime.now(timezone.utc).isoformat()
        context = state.get("context", {})
        context["injections"] = injections

        await state_manager.update_run(
            run_id,
            {"pending_steps": pending, "context": context},
            expected_etag=expected_etag,
        )

        return RunActionResponse(
            run_id=run_id,
            status=state["status"],
            message=f"Step '{request.step_id}' injected at position '{request.position}'",
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.post("/{run_id}/interrupt", response_model=RunActionResponse)
async def interrupt_run(
    run_id: str,
    request: InterruptRequest,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Interrupt a run with a detour.

    Pauses the current run and optionally executes a detour flow/steps
    before resuming.

    Args:
        run_id: Run identifier.
        request: Interrupt request with detour details.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response with interrupt details.

    Raises:
        404: Run not found.
        409: Run is not in an interruptible state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    try:
        state, _ = await state_manager.get_run(run_id)

        if state["status"] not in ("running", "pending"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot interrupt run with status '{state['status']}'",
                    "details": {"current_status": state["status"]},
                },
            )

        now = datetime.now(timezone.utc).isoformat()

        # Build interruption context
        context = state.get("context", {})
        interruptions = context.get("interruptions", [])
        interruptions.append(
            {
                "reason": request.reason,
                "detour_flow": request.detour_flow,
                "detour_steps": request.detour_steps,
                "resume_after": request.resume_after,
                "interrupted_at": now,
                "interrupted_step": state.get("current_step"),
            }
        )
        context["interruptions"] = interruptions

        # Inject detour steps if specified
        pending = state.get("pending_steps", [])
        if request.detour_steps:
            pending = list(request.detour_steps) + pending

        await state_manager.update_run(
            run_id,
            {
                "status": "paused",
                "paused_at": now,
                "pending_steps": pending,
                "context": context,
            },
            expected_etag=expected_etag,
        )

        detour_info = ""
        if request.detour_flow:
            detour_info = f" with detour flow '{request.detour_flow}'"
        elif request.detour_steps:
            detour_info = f" with {len(request.detour_steps)} detour step(s)"

        return RunActionResponse(
            run_id=run_id,
            status="paused",
            message=f"Run interrupted: {request.reason}{detour_info}",
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.delete("/{run_id}", response_model=RunActionResponse)
async def cancel_run(
    run_id: str,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Cancel a run.

    Terminates the run and marks it as canceled. This is irreversible.

    Args:
        run_id: Run identifier.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response confirming cancellation.

    Raises:
        404: Run not found.
        409: Run is already completed.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    try:
        state, _ = await state_manager.get_run(run_id)

        if state["status"] in ("succeeded", "failed", "canceled", "stopped"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot cancel run with status '{state['status']}'",
                    "details": {"current_status": state["status"]},
                },
            )

        now = datetime.now(timezone.utc).isoformat()
        await state_manager.update_run(
            run_id,
            {"status": "canceled", "completed_at": now},
            expected_etag=expected_etag,
        )

        return RunActionResponse(
            run_id=run_id,
            status="canceled",
            message="Run canceled successfully",
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.post("/{run_id}/stop", response_model=StopResponse)
async def stop_run(
    run_id: str,
    request: StopRequest,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Stop a run gracefully with savepoint.

    Initiates a graceful shutdown of the run:
    1. Sets status to "stopping"
    2. Drains remaining messages with timeout
    3. Persists run_state.json with status="stopped"
    4. Writes stop_report.md with forensic information

    Unlike cancel, stop creates a clean savepoint that can be resumed.
    The UI should show "stopping..." then "stopped" (not "failed").

    Args:
        run_id: Run identifier.
        request: Stop request with reason and timeout.
        if_match: Optional ETag for concurrency control.

    Returns:
        StopResponse with stop report path and info.

    Raises:
        404: Run not found.
        409: Run is not in a stoppable state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    try:
        state, _ = await state_manager.get_run(run_id)
        current_status = state["status"]

        # Only allow stopping runs that are running, pending, or paused
        if current_status not in ("running", "pending", "paused", "pausing"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot stop run with status '{current_status}'",
                    "details": {"current_status": current_status},
                },
            )

        now = datetime.now(timezone.utc).isoformat()

        # First, set status to "stopping"
        await state_manager.update_run(
            run_id,
            {"status": "stopping"},
            expected_etag=expected_etag,
        )

        # Emit stopping event for SSE subscribers
        from .events import EventType, write_event_sync

        write_event_sync(
            run_id=run_id,
            runs_root=state_manager.runs_root,
            event_type=EventType.RUN_STOPPING,
            data={
                "run_id": run_id,
                "previous_status": current_status,
                "current_step": state.get("current_step"),
                "stopping_at": now,
                "reason": request.reason,
            },
        )

        # Collect stop report info
        stop_info = StopReportInfo(
            last_step_id=state.get("current_step"),
            last_routing_intent=state.get("context", {}).get("last_routing_intent"),
            last_tool_calls=state.get("context", {}).get("recent_tool_calls", [])[-10:],
            open_assumptions=state.get("context", {}).get("assumptions", []),
            stop_reason=request.reason,
            stopped_at=now,
        )

        # Write stop report
        stop_report_path = await _write_stop_report(
            run_id=run_id,
            runs_root=state_manager.runs_root,
            stop_info=stop_info,
            state=state,
        )

        # Now transition to "stopped"
        await state_manager.update_run(
            run_id,
            {
                "status": "stopped",
                "stopped_at": now,
                "stop_reason": {
                    "type": request.reason,
                    "timestamp": now,
                    "drain_timeout_ms": request.drain_timeout_ms,
                },
            },
        )

        # Emit stopped event
        write_event_sync(
            run_id=run_id,
            runs_root=state_manager.runs_root,
            event_type=EventType.RUN_STOPPED,
            data={
                "run_id": run_id,
                "current_step": state.get("current_step"),
                "stopped_at": now,
                "reason": request.reason,
                "stop_report_path": stop_report_path,
            },
        )

        return StopResponse(
            run_id=run_id,
            status="stopped",
            message=f"Run stopped gracefully: {request.reason}",
            timestamp=now,
            stop_report_path=stop_report_path,
            stop_info=stop_info,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


async def _write_stop_report(
    run_id: str,
    runs_root: Path,
    stop_info: StopReportInfo,
    state: Dict[str, Any],
) -> str:
    """Write stop_report.md with forensic information.

    Args:
        run_id: Run identifier.
        runs_root: Root directory for runs.
        stop_info: Collected stop information.
        state: Current run state.

    Returns:
        Relative path to the stop report file.
    """
    run_dir = runs_root / run_id
    report_path = run_dir / "stop_report.md"

    # Build report content
    lines = [
        "# Stop Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Stopped At:** {stop_info.stopped_at}",
        f"**Reason:** {stop_info.stop_reason}",
        "",
        "## Execution State",
        "",
        f"- **Last Step ID:** {stop_info.last_step_id or 'None'}",
        f"- **Flow ID:** {state.get('flow_id', 'Unknown')}",
        f"- **Previous Status:** {state.get('status', 'Unknown')}",
        "",
    ]

    # Add routing intent if available
    if stop_info.last_routing_intent:
        lines.extend(
            [
                "## Last Routing Intent",
                "",
                "```",
                stop_info.last_routing_intent,
                "```",
                "",
            ]
        )

    # Add recent tool calls
    if stop_info.last_tool_calls:
        lines.extend(
            [
                "## Last Tool Calls (paths only)",
                "",
            ]
        )
        for call in stop_info.last_tool_calls:
            lines.append(f"- `{call}`")
        lines.append("")

    # Add open assumptions
    if stop_info.open_assumptions:
        lines.extend(
            [
                "## Open Assumptions/Decisions",
                "",
            ]
        )
        for assumption in stop_info.open_assumptions:
            lines.append(f"- {assumption}")
        lines.append("")

    # Add completed steps if available
    completed_steps = state.get("completed_steps", [])
    if completed_steps:
        lines.extend(
            [
                "## Completed Steps",
                "",
            ]
        )
        for step in completed_steps:
            lines.append(f"- {step}")
        lines.append("")

    # Add pending steps if available
    pending_steps = state.get("pending_steps", [])
    if pending_steps:
        lines.extend(
            [
                "## Pending Steps (not executed)",
                "",
            ]
        )
        for step in pending_steps:
            lines.append(f"- {step}")
        lines.append("")

    # Write the report
    report_content = "\n".join(lines)
    report_path.write_text(report_content, encoding="utf-8")

    return str(report_path.relative_to(runs_root.parent))
