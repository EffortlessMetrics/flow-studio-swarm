"""
orchestrator.py - Thin StepwiseOrchestrator coordinator.

This module provides a thin orchestrator that delegates to the modular
components in the stepwise package. It coordinates:

1. Run lifecycle (create/resume)
2. Step iteration loop
3. Routing decisions
4. Event persistence

The heavy lifting is done by:
- spec_facade: Loading and caching specs
- routing: Creating routing signals and determining next steps
- receipt_compat: Reading/writing receipt fields

This orchestrator is designed to be ~200 lines (vs 2962 in the original)
by delegating to focused modules.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from swarm.config.flow_registry import (
    FlowDefinition,
    FlowRegistry,
    StepDefinition,
)
from swarm.runtime import storage as storage_module
from swarm.runtime.engines import StepEngine, StepContext
from swarm.runtime.engines.models import RoutingContext
from swarm.runtime.types import (
    HandoffEnvelope,
    RoutingDecision,
    RoutingSignal,
    RunEvent,
    RunId,
    RunSpec,
    RunState,
    RunStatus,
    SDLCStatus,
    RunSummary,
    generate_run_id,
)

from .receipt_compat import read_receipt_field, update_receipt_routing
from .routing import create_routing_signal, route_step, build_routing_context
from .spec_facade import SpecFacade

if TYPE_CHECKING:
    from swarm.runtime.navigator_integration import NavigationOrchestrator

logger = logging.getLogger(__name__)

# Maximum nested detour depth (prevents runaway sidequests)
MAX_DETOUR_DEPTH = 10


class StepwiseOrchestrator:
    """Thin orchestrator for stepwise flow execution.

    This class coordinates step-by-step flow execution while delegating
    the actual work to focused modules. It provides:

    - Run creation and metadata persistence
    - Flow definition loading from flow_registry
    - Per-step context building and engine invocation
    - Event aggregation into run's events.jsonl

    Attributes:
        _engine: The StepEngine instance for executing steps.
        _repo_root: Root path of the repository.
        _spec_facade: Facade for loading FlowSpec/StationSpec.
    """

    def __init__(
        self,
        engine: StepEngine,
        repo_root: Optional[Path] = None,
        use_spec_bridge: bool = False,
    ):
        """Initialize the orchestrator.

        Args:
            engine: StepEngine instance for executing steps.
            repo_root: Repository root path. Defaults to auto-detection.
            use_spec_bridge: If True, load flows from JSON specs.
        """
        self._engine = engine
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._flow_registry = FlowRegistry.get_instance()
        self._use_spec_bridge = use_spec_bridge
        self._spec_facade = SpecFacade(self._repo_root)
        self._lock = threading.Lock()

        # Stop request tracking for graceful interruption
        self._stop_requests: Dict[RunId, threading.Event] = {}

    def request_stop(self, run_id: RunId) -> bool:
        """Request graceful stop of a running run.

        Args:
            run_id: The run to stop.

        Returns:
            True if stop was signaled, False if run not found.
        """
        with self._lock:
            if run_id not in self._stop_requests:
                self._stop_requests[run_id] = threading.Event()

        self._stop_requests[run_id].set()
        logger.info("Stop requested for run %s", run_id)
        return True

    def clear_stop_request(self, run_id: RunId) -> None:
        """Clear any pending stop request for a run."""
        if run_id in self._stop_requests:
            self._stop_requests[run_id].clear()

    def _is_stop_requested(self, run_id: RunId) -> bool:
        """Check if stop has been requested for a run."""
        if run_id not in self._stop_requests:
            return False
        return self._stop_requests[run_id].is_set()

    def run_stepwise_flow(
        self,
        flow_key: str,
        spec: RunSpec,
        resume: bool = False,
        run_id: Optional[RunId] = None,
    ) -> RunId:
        """Execute a flow step by step.

        Args:
            flow_key: The flow to execute (e.g., "build", "plan").
            spec: The run specification.
            resume: Whether to resume an existing run.
            run_id: Optional run ID for resuming.

        Returns:
            The run ID.
        """
        # Generate or use provided run ID
        if run_id is None:
            run_id = generate_run_id()

        # Initialize stop tracking
        with self._lock:
            if run_id not in self._stop_requests:
                self._stop_requests[run_id] = threading.Event()

        if resume:
            self.clear_stop_request(run_id)

        # Load flow definition
        flow_def = self._flow_registry.get_flow(flow_key)
        if flow_def is None:
            raise ValueError(f"Unknown flow: {flow_key}")

        # Create run directory and initial state
        storage_module.init_run(run_id, flow_key, spec)

        # Emit run_started event
        storage_module.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=datetime.now(timezone.utc),
                kind="run_started",
                flow_key=flow_key,
                step_id=None,
                payload={"spec": spec.__dict__ if hasattr(spec, "__dict__") else {}},
            ),
        )

        # Execute steps
        try:
            summary = self._execute_stepwise(
                run_id, flow_key, flow_def, spec, resume=resume
            )
            return run_id
        except Exception as e:
            logger.error("Run %s failed: %s", run_id, e)
            storage_module.append_event(
                run_id,
                RunEvent(
                    run_id=run_id,
                    ts=datetime.now(timezone.utc),
                    kind="run_failed",
                    flow_key=flow_key,
                    step_id=None,
                    payload={"error": str(e)},
                ),
            )
            raise

    def _execute_stepwise(
        self,
        run_id: RunId,
        flow_key: str,
        flow_def: FlowDefinition,
        spec: RunSpec,
        resume: bool = False,
    ) -> RunSummary:
        """Execute flow steps sequentially.

        Args:
            run_id: The run identifier.
            flow_key: The flow key.
            flow_def: The flow definition.
            spec: The run specification.
            resume: Whether resuming an existing run.

        Returns:
            RunSummary with final status.
        """
        history: List[Dict[str, Any]] = []
        loop_state: Dict[str, int] = {}
        current_step_idx = 0
        steps = flow_def.steps

        if not steps:
            return RunSummary(
                run_id=run_id,
                status=RunStatus.SUCCEEDED,
                sdlc_status=SDLCStatus.OK,
                flow_key=flow_key,
                completed_steps=[],
                duration_ms=0,
            )

        while current_step_idx < len(steps):
            # Check for stop request
            if self._is_stop_requested(run_id):
                logger.info("Stop requested, pausing run %s at step %d", run_id, current_step_idx)
                storage_module.append_event(
                    run_id,
                    RunEvent(
                        run_id=run_id,
                        ts=datetime.now(timezone.utc),
                        kind="run_stopped",
                        flow_key=flow_key,
                        step_id=steps[current_step_idx].id,
                        payload={"step_index": current_step_idx},
                    ),
                )
                break

            step = steps[current_step_idx]

            # Build routing context for this step
            routing_ctx = build_routing_context(step, loop_state)

            # Build step context
            ctx = StepContext(
                repo_root=self._repo_root,
                run_id=run_id,
                flow_key=flow_key,
                step_id=step.id,
                step_index=step.index,
                total_steps=len(steps),
                spec=spec,
                flow_title=flow_def.title,
                step_role=step.role,
                step_agents=tuple(step.agents) if step.agents else (),
                history=history,
                routing=routing_ctx,
            )

            # Execute step
            step_result, events = self._engine.run_step(ctx)

            # Persist events
            for event in events:
                storage_module.append_event(run_id, event)

            # Add to history
            history.append({
                "step_id": step.id,
                "status": step_result.status,
                "output": step_result.output,
                "duration_ms": step_result.duration_ms,
            })

            # Create routing signal
            result_dict = {
                "run_id": run_id,
                "flow_key": flow_key,
                "status": step_result.status,
            }

            # Create receipt reader for routing
            def make_receipt_reader():
                repo_root = self._repo_root
                return lambda r, f, s, a, field: read_receipt_field(
                    repo_root, r, f, s, a, field
                )

            # Route to next step
            next_step_id, reason = route_step(
                flow_def=flow_def,
                current_step=step,
                result=result_dict,
                loop_state=loop_state,
                run_id=run_id,
                flow_key=flow_key,
                receipt_reader=make_receipt_reader(),
            )

            # Update routing context with decision
            routing_ctx.decision = "advance" if next_step_id else "terminate"
            routing_ctx.reason = reason

            # Update receipt with routing info
            if step.agents:
                update_receipt_routing(
                    self._repo_root, run_id, flow_key, step.id, step.agents[0], routing_ctx
                )

            # Emit routing event
            storage_module.append_event(
                run_id,
                RunEvent(
                    run_id=run_id,
                    ts=datetime.now(timezone.utc),
                    kind="step_routed",
                    flow_key=flow_key,
                    step_id=step.id,
                    payload={
                        "next_step_id": next_step_id,
                        "reason": reason,
                    },
                ),
            )

            if next_step_id is None:
                # Flow complete
                break

            # Find next step by ID
            found = False
            for i, s in enumerate(steps):
                if s.id == next_step_id:
                    current_step_idx = i
                    found = True
                    break

            if not found:
                logger.error("Next step %s not found in flow", next_step_id)
                break

        # Emit run_completed event
        storage_module.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=datetime.now(timezone.utc),
                kind="run_completed",
                flow_key=flow_key,
                step_id=None,
                payload={"steps_completed": len(history)},
            ),
        )

        return RunSummary(
            run_id=run_id,
            status=RunStatus.SUCCEEDED,
            sdlc_status=SDLCStatus.OK,
            flow_key=flow_key,
            completed_steps=[h["step_id"] for h in history],
            duration_ms=sum(h.get("duration_ms", 0) for h in history),
        )


# Backwards compatibility alias
GeminiStepOrchestrator = StepwiseOrchestrator

def get_orchestrator(
    engine: Optional[StepEngine] = None,
    repo_root: Optional[Path] = None,
) -> StepwiseOrchestrator:
    """Factory function to create a stepwise orchestrator.

    Args:
        engine: Optional StepEngine instance. Creates GeminiStepEngine if None.
        repo_root: Optional repository root path.

    Returns:
        Configured StepwiseOrchestrator instance.
    """
    from swarm.runtime.engines import GeminiStepEngine

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]

    if engine is None:
        engine = GeminiStepEngine(repo_root)

    return StepwiseOrchestrator(engine=engine, repo_root=repo_root)


__all__ = [
    "StepwiseOrchestrator",
    "GeminiStepOrchestrator",
    "get_orchestrator",
]
