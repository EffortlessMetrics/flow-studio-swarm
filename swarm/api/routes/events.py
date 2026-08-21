"""Server-Sent Events as a transport projection of canonical RunEvent rows."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from swarm.runtime import storage
from swarm.runtime.safe_paths import validate_path_component
from swarm.runtime.types import RunEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runs", tags=["events"])


class EventType:
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    HEARTBEAT = "heartbeat"

    RUN_STARTED = "run:started"
    RUN_PAUSED = "run:paused"
    RUN_PAUSING = "run:pausing"
    RUN_RESUMED = "run:resumed"
    RUN_COMPLETED = "run:completed"
    RUN_FAILED = "run:failed"
    RUN_CANCELED = "run:canceled"
    RUN_INTERRUPTED = "run:interrupted"
    RUN_STOPPING = "run:stopping"
    RUN_STOPPED = "run:stopped"

    FLOW_COMPLETED = "flow:completed"
    PLAN_COMPLETED = "plan:completed"

    STEP_STARTED = "step:started"
    STEP_PROGRESS = "step:progress"
    STEP_COMPLETED = "step:completed"
    STEP_FAILED = "step:failed"
    STEP_SKIPPED = "step:skipped"

    ARTIFACT_CREATED = "artifact:created"
    ARTIFACT_UPDATED = "artifact:updated"

    LLM_STARTED = "llm:started"
    LLM_TOKEN = "llm:token"
    LLM_COMPLETED = "llm:completed"

    WISDOM_PATCH_APPLIED = "wisdom:patch_applied"
    WISDOM_PATCH_REJECTED = "wisdom:patch_rejected"
    WISDOM_PATCH_VALIDATED = "wisdom:patch_validated"
    WISDOM_AUTO_APPLY_STARTED = "wisdom:auto_apply_started"
    WISDOM_AUTO_APPLY_COMPLETED = "wisdom:auto_apply_completed"

    ERROR = "error"


_KIND_TO_SSE = {
    "run_started": EventType.RUN_STARTED,
    "run_pausing": EventType.RUN_PAUSING,
    "flow_paused": EventType.RUN_PAUSED,
    "run_paused": EventType.RUN_PAUSED,
    "run_resumed": EventType.RUN_RESUMED,
    "run_completed": EventType.RUN_COMPLETED,
    "run_failed": EventType.RUN_FAILED,
    "run_canceled": EventType.RUN_CANCELED,
    "run_cancelled": EventType.RUN_CANCELED,
    "run_interrupted": EventType.RUN_INTERRUPTED,
    "run_stopping": EventType.RUN_STOPPING,
    "run_stopped": EventType.RUN_STOPPED,
    "step_start": EventType.STEP_STARTED,
    "step_started": EventType.STEP_STARTED,
    "step_progress": EventType.STEP_PROGRESS,
    "step_end": EventType.STEP_COMPLETED,
    "step_completed": EventType.STEP_COMPLETED,
    "step_failed": EventType.STEP_FAILED,
    "step_skipped": EventType.STEP_SKIPPED,
    "flow_completed": EventType.FLOW_COMPLETED,
    "autopilot_flow_completed": EventType.FLOW_COMPLETED,
    "autopilot_completed": EventType.PLAN_COMPLETED,
}
_SSE_TO_KIND = {
    EventType.RUN_STARTED: "run_started",
    EventType.RUN_PAUSING: "run_pausing",
    EventType.RUN_PAUSED: "run_paused",
    EventType.RUN_RESUMED: "run_resumed",
    EventType.RUN_COMPLETED: "run_completed",
    EventType.RUN_FAILED: "run_failed",
    EventType.RUN_CANCELED: "run_canceled",
    EventType.RUN_INTERRUPTED: "run_interrupted",
    EventType.RUN_STOPPING: "run_stopping",
    EventType.RUN_STOPPED: "run_stopped",
    EventType.FLOW_COMPLETED: "flow_completed",
    EventType.PLAN_COMPLETED: "autopilot_completed",
    EventType.STEP_STARTED: "step_start",
    EventType.STEP_PROGRESS: "step_progress",
    EventType.STEP_COMPLETED: "step_end",
    EventType.STEP_FAILED: "step_failed",
    EventType.STEP_SKIPPED: "step_skipped",
}
_TERMINAL_EVENT_TYPES = frozenset(
    {
        EventType.RUN_COMPLETED,
        EventType.RUN_FAILED,
        EventType.RUN_CANCELED,
        EventType.RUN_STOPPED,
        EventType.PLAN_COMPLETED,
    }
)
_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "canceled", "stopped"})


def format_sse_event(
    event_type: str,
    data: Dict[str, Any],
    event_id: Optional[str] = None,
    retry: Optional[int] = None,
) -> str:
    """Format one transport event without mutating its durable source row."""
    payload = dict(data)
    payload.setdefault(
        "timestamp",
        payload.get("ts") or datetime.now(timezone.utc).isoformat(),
    )
    payload.setdefault("type", event_type.replace(":", "_"))

    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    if event_type:
        lines.append(f"event: {event_type}")
    if retry:
        lines.append(f"retry: {retry}")
    lines.append(f"data: {json.dumps(payload)}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _transport_event_type(record: Dict[str, Any]) -> str:
    kind = record.get("kind")
    if isinstance(kind, str) and kind:
        return _KIND_TO_SSE.get(kind, kind)

    legacy_event = record.get("event")
    if isinstance(legacy_event, str) and legacy_event:
        return _KIND_TO_SSE.get(legacy_event, legacy_event)

    return "message"


async def read_events_file(
    events_file: Path,
    last_position: int = 0,
) -> tuple[list[Dict[str, Any]], int]:
    """Read complete JSONL rows after ``last_position``."""
    if not events_file.exists():
        return [], last_position

    events: list[Dict[str, Any]] = []
    new_position = last_position
    try:
        with events_file.open("r", encoding="utf-8") as stream:
            stream.seek(last_position)
            for line in stream:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    events.append(json.loads(stripped))
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in events file: %s", stripped)
            new_position = stream.tell()
    except OSError as exc:
        logger.warning("Error reading events file %s: %s", events_file, exc)
    return events, new_position


async def generate_run_events(
    run_id: str,
    runs_root: Path,
    poll_interval: float = 1.0,
    heartbeat_interval: float = 15.0,
) -> AsyncGenerator[str, None]:
    """Stream canonical journal rows and state-derived heartbeats."""
    validate_path_component(run_id, "run_id")
    run_dir = runs_root / run_id
    events_file = run_dir / "events.jsonl"
    state_file = run_dir / "run_state.json"

    last_position = 0
    last_heartbeat = datetime.now(timezone.utc)
    event_counter = 1
    terminal_emitted = False

    yield format_sse_event(
        EventType.CONNECTED,
        {"run_id": run_id, "message": "Connected to event stream"},
        event_id=str(event_counter),
    )

    while True:
        try:
            if not state_file.exists():
                yield format_sse_event(
                    EventType.ERROR,
                    {"error": "run_not_found", "message": f"Run '{run_id}' not found"},
                )
                return

            state = json.loads(state_file.read_text(encoding="utf-8"))
            status = state.get("status", "pending")
            records, last_position = await read_events_file(events_file, last_position)

            for record in records:
                event_counter += 1
                event_type = _transport_event_type(record)
                terminal_emitted = terminal_emitted or event_type in _TERMINAL_EVENT_TYPES
                durable_id = record.get("event_id")
                yield format_sse_event(
                    event_type,
                    record,
                    event_id=str(durable_id or event_counter),
                )

            now = datetime.now(timezone.utc)
            if (now - last_heartbeat).total_seconds() >= heartbeat_interval:
                event_counter += 1
                current_step = (
                    state.get("current_step_id")
                    or state.get("current_node")
                    or state.get("current_step")
                )
                yield format_sse_event(
                    EventType.HEARTBEAT,
                    {"run_id": run_id, "status": status, "current_step": current_step},
                    event_id=str(event_counter),
                )
                last_heartbeat = now

            if status in _TERMINAL_STATUSES:
                if not terminal_emitted:
                    event_counter += 1
                    status_to_event = {
                        "succeeded": EventType.RUN_COMPLETED,
                        "failed": EventType.RUN_FAILED,
                        "canceled": EventType.RUN_CANCELED,
                        "stopped": EventType.RUN_STOPPED,
                    }
                    yield format_sse_event(
                        status_to_event[status],
                        {
                            "run_id": run_id,
                            "status": status,
                            "completed_at": state.get("completed_at"),
                            "stopped_at": state.get("stopped_at"),
                            "error": state.get("error"),
                            "stop_reason": state.get("stop_reason"),
                        },
                        event_id=str(event_counter),
                    )
                return

            await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.debug("SSE client disconnected for run %s", run_id)
            return
        except Exception as exc:
            logger.exception("Error in event stream for run %s", run_id)
            yield format_sse_event(
                EventType.ERROR,
                {"error": "stream_error", "message": str(exc)},
            )
            await asyncio.sleep(5)


@router.get("/{run_id}/events")
async def stream_run_events(run_id: str, request: Request):
    """Stream one run's canonical journal as SSE."""
    try:
        validate_path_component(run_id, "run_id")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from ..server import get_spec_manager

    runs_root = get_spec_manager().runs_root
    try:
        from swarm.runtime.resilient_db import check_db_health

        check_db_health()
    except Exception as exc:
        logger.warning("DB health check failed on SSE connect: %s", exc)

    if not (runs_root / run_id).is_dir():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )

    async def event_stream():
        async for event in generate_run_events(run_id, runs_root):
            if await request.is_disconnected():
                return
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _canonical_event_from_transport(
    run_id: str,
    event_type: str,
    data: Dict[str, Any],
) -> RunEvent:
    payload = dict(data)
    payload.pop("run_id", None)
    flow_key = str(payload.pop("flow_key", ""))
    step_id = payload.pop("step_id", None)
    agent_key = payload.pop("agent_key", None)
    payload.pop("event", None)
    payload.pop("kind", None)
    payload.pop("event_id", None)
    payload.pop("seq", None)
    payload.pop("ts", None)
    payload.pop("timestamp", None)
    payload.pop("type", None)

    kind = _SSE_TO_KIND.get(event_type, event_type.replace(":", "_"))
    return RunEvent(
        run_id=run_id,
        ts=datetime.now(timezone.utc),
        kind=kind,
        flow_key=flow_key,
        step_id=step_id,
        agent_key=agent_key,
        payload=payload,
    )


async def write_event(
    run_id: str,
    runs_root: Path,
    event_type: str,
    data: Dict[str, Any],
) -> None:
    """Compatibility writer that persists a canonical RunEvent row."""
    validate_path_component(run_id, "run_id")
    storage.append_event(
        run_id,
        _canonical_event_from_transport(run_id, event_type, data),
        runs_root,
    )


def write_event_sync(
    run_id: str,
    runs_root: Path,
    event_type: str,
    data: Dict[str, Any],
) -> None:
    """Synchronous compatibility writer for control endpoints."""
    validate_path_component(run_id, "run_id")
    storage.append_event(
        run_id,
        _canonical_event_from_transport(run_id, event_type, data),
        runs_root,
    )
