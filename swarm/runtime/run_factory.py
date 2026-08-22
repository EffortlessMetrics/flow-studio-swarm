"""Canonical run initialization for every Flow Studio entry point.

The initializer returns only after its durable launch record exists:
``spec.json``, ``meta.json``, ``run_state.json``, and the initial
``run_created`` event. Individual files are atomically replaced by the
storage layer; directory publication across the four files is not atomic.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import storage
from .types import (
    RunEvent,
    RunId,
    RunSpec,
    RunState,
    RunStatus,
    RunSummary,
    SDLCStatus,
)


@dataclass(frozen=True)
class InitializedRun:
    """The durable objects created for one run identity."""

    run_id: RunId
    spec: RunSpec
    summary: RunSummary
    state: RunState
    path: Path


def initialize_run(
    run_id: RunId,
    spec: RunSpec,
    *,
    flow_key: Optional[str] = None,
    start_step: Optional[str] = None,
    mode: str = "execute",
    runs_dir: Path = storage.RUNS_DIR,
) -> InitializedRun:
    """Create one complete durable launch record or raise before returning it.

    Individual files may be visible while initialization is in progress;
    callers must treat successful return as the publication boundary. The
    per-run ``spec.json`` is scoped by its containing run directory; the run
    identity is repeated in metadata, runtime state, and every event where it
    is semantically part of the record.

    Args:
        run_id: Stable identity selected by the caller.
        spec: Execution intent for the run.
        flow_key: Initial flow. Defaults to the first flow in ``spec``.
        start_step: Optional initial program-counter node.
        mode: Requested API mode (execute, preview, or validate).
        runs_dir: Canonical run root.

    Returns:
        The initialized durable objects.

    Raises:
        FileExistsError: A non-empty run directory already owns ``run_id``.
        ValueError: No initial flow can be derived.
        RuntimeError: The constitutional journal row could not be persisted.
    """
    initial_flow = flow_key or (spec.flow_keys[0] if spec.flow_keys else None)
    if not initial_flow:
        raise ValueError("A canonical run requires at least one flow")

    run_path = storage.get_run_path(run_id, runs_dir)
    if run_path.exists() and any(run_path.iterdir()):
        raise FileExistsError(f"Run already exists: {run_id}")

    created_new_directory = not run_path.exists()
    now = datetime.now(timezone.utc)
    state = RunState(
        run_id=run_id,
        flow_key=initial_flow,
        current_step_id=start_step,
        status=RunStatus.PENDING.value,
        timestamp=now,
    )
    summary = RunSummary(
        id=run_id,
        spec=spec,
        status=RunStatus.PENDING,
        sdlc_status=SDLCStatus.UNKNOWN,
        created_at=now,
        updated_at=now,
        path=str(run_path),
    )

    try:
        storage.create_run_dir(run_id, runs_dir)
        storage.write_spec(run_id, spec, runs_dir)
        storage.write_summary(run_id, summary, runs_dir)
        storage.write_run_state(run_id, state, runs_dir)
        storage.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=now,
                kind="run_created",
                flow_key=initial_flow,
                payload={
                    "status": RunStatus.PENDING.value,
                    "mode": mode,
                    "backend": spec.backend,
                    "initiator": spec.initiator,
                    "flow_keys": list(spec.flow_keys),
                },
            ),
            runs_dir,
        )

        events = storage.read_events(run_id, runs_dir)
        if not events or events[0].kind != "run_created" or events[0].run_id != run_id:
            raise RuntimeError(f"Failed to persist canonical run_created event for {run_id}")
    except Exception:
        if created_new_directory and run_path.exists():
            shutil.rmtree(run_path, ignore_errors=True)
        raise

    return InitializedRun(
        run_id=run_id,
        spec=spec,
        summary=summary,
        state=state,
        path=run_path,
    )
