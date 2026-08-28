"""stepwise_gemini - Gemini stepwise orchestrator backend adapter.

Adapts the Gemini stepwise orchestrator to the RunBackend interface
(one LLM call per step rather than one per flow).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from .. import storage
from ..types import (
    BackendCapabilities,
    BackendId,
    RunEvent,
    RunId,
    RunSpec,
    RunState,
    RunStatus,
    RunSummary,
    SDLCStatus,
    generate_run_id,
)
from .base import RunBackend

logger = logging.getLogger(__name__)



class GeminiStepwiseBackend(RunBackend):
    """Backend that uses GeminiStepOrchestrator for stepwise flow execution.

    This backend provides fine-grained control over flow execution by
    iterating through each step of a flow as a separate Gemini CLI call.
    This enables:

    - Per-step observability with events logged at step boundaries
    - Context handoff between steps (previous outputs inform next step)
    - Better error isolation (failures are step-scoped)
    - Teaching mode support (can pause/resume at step boundaries)

    Unlike GeminiCliBackend which executes entire flows in one call, this
    backend delegates to GeminiStepOrchestrator which breaks down flows
    into individual steps.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._orchestrator: Optional[Any] = None  # Type: GeminiStepOrchestrator
        self._lock = threading.Lock()

    def _get_orchestrator(self) -> Any:
        """Lazy-initialize the orchestrator (thread-safe).

        Uses lazy import to avoid circular dependency with orchestrator module.
        Uses double-checked locking to ensure thread-safe initialization.
        """
        if self._orchestrator is None:
            with self._lock:
                # Double-check after acquiring lock
                if self._orchestrator is None:
                    # Lazy import to avoid circular dependency
                    from ..orchestrator import get_orchestrator

                    self._orchestrator = get_orchestrator(repo_root=self._repo_root)
        return self._orchestrator

    @property
    def id(self) -> BackendId:
        return "gemini-step-orchestrator"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            id="gemini-step-orchestrator",
            label="Gemini CLI (stepwise)",
            supports_streaming=True,
            supports_events=True,
            supports_cancel=True,
            supports_replay=False,
        )

    def start(self, spec: RunSpec) -> RunId:
        """Start a stepwise run by invoking the orchestrator.

        Synchronous Guarantees (on return):
        - run_id: Unique ID generated (format: run-YYYYMMDD-HHMMSS-xxxxxx)
        - run directory: swarm/runs/<run_id>/ created
        - spec.json: RunSpec persisted
        - meta.json: Initial RunSummary with status=PENDING
        - events.jsonl: run_created event with stepwise=True

        Asynchronous Work (background thread):
        - Actual step execution delegated to orchestrator
        - Status updates (RUNNING, SUCCEEDED, FAILED)
        - Poll get_summary() or get_events() to track progress
        """
        run_id = generate_run_id()
        now = datetime.now(timezone.utc)

        # Create run directory and write initial metadata
        storage.create_run_dir(run_id)
        storage.write_spec(run_id, spec)

        summary = RunSummary(
            id=run_id,
            spec=spec,
            status=RunStatus.PENDING,
            sdlc_status=SDLCStatus.UNKNOWN,
            created_at=now,
            updated_at=now,
        )
        storage.write_summary(run_id, summary)

        # Log initial event with stepwise flag
        storage.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=now,
                kind="run_created",
                flow_key=spec.flow_keys[0] if spec.flow_keys else "unknown",
                payload={
                    "flows": spec.flow_keys,
                    "backend": "gemini-step-orchestrator",
                    "initiator": spec.initiator,
                    "stepwise": True,
                },
            ),
        )

        # Start orchestrator execution in background thread
        thread = threading.Thread(
            target=self._execute_stepwise,
            args=(run_id, spec),
            daemon=True,
        )
        thread.start()

        return run_id

    def _execute_stepwise(self, run_id: RunId, spec: RunSpec) -> None:
        """Execute the stepwise flow via the orchestrator.

        This method runs in a background thread and delegates to the
        GeminiStepOrchestrator for step-by-step execution.
        """
        orchestrator = self._get_orchestrator()

        # Execute each flow in the spec
        for flow_key in spec.flow_keys:
            try:
                # Create RunState for this flow execution
                run_state = RunState(
                    run_id=run_id,
                    flow_key=flow_key,
                    status="pending",
                    timestamp=datetime.now(timezone.utc),
                )
                storage.write_run_state(run_id, run_state)

                # The orchestrator handles its own run creation, but we want
                # to use our run_id. We call run_stepwise_flow which creates
                # its own run_id, so we need to manually drive the execution.
                # For now, we invoke the orchestrator's internal execution method.
                orchestrator._execute_stepwise(
                    run_id=run_id,
                    flow_key=flow_key,
                    flow_def=orchestrator._flow_registry.get_flow(flow_key),
                    spec=spec,
                    run_state=run_state,
                    start_step=None,
                    end_step=None,
                )
            except Exception as e:
                logger.exception(
                    "Error in stepwise execution for run %s, flow %s",
                    run_id,
                    flow_key,
                )
                # Update summary with error
                now = datetime.now(timezone.utc)
                storage.update_summary(
                    run_id,
                    {
                        "status": RunStatus.FAILED.value,
                        "sdlc_status": SDLCStatus.ERROR.value,
                        "completed_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "error": str(e),
                    },
                )
                return  # Exit on error

        # All flows completed successfully - update status
        now = datetime.now(timezone.utc)
        storage.update_summary(
            run_id,
            {
                "status": RunStatus.SUCCEEDED.value,
                "sdlc_status": SDLCStatus.OK.value,
                "completed_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
        )

    def get_summary(self, run_id: RunId) -> Optional[RunSummary]:
        """Get summary from disk."""
        return storage.read_summary(run_id)

    def list_summaries(self) -> List[RunSummary]:
        """List all runs with summaries."""
        summaries: List[RunSummary] = []
        for rid in storage.list_runs():
            summary = storage.read_summary(rid)
            if summary:
                summaries.append(summary)
        return summaries

    def get_events(self, run_id: RunId) -> List[RunEvent]:
        """Get events from disk."""
        return storage.read_events(run_id)

    def cancel(self, run_id: RunId) -> bool:
        """Cancel a running stepwise execution.

        Note: Currently returns False as the orchestrator does not yet
        support mid-execution cancellation. The orchestrator would need
        to track running state per run_id to support this.
        """
        # TODO: Implement cancellation by tracking orchestrator run state
        return False
