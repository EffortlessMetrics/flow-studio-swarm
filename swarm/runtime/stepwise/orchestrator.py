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

# A3: Envelope-first routing imports
from swarm.runtime.handoff_io import (
    read_routing_from_envelope,
    update_envelope_routing,
)
from swarm.runtime.routing_utils import parse_routing_decision
from swarm.runtime.router import FlowGraph, Edge, NodeConfig  # For Navigator integration

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
        navigation_orchestrator: Optional["NavigationOrchestrator"] = None,
    ):
        """Initialize the orchestrator.

        Args:
            engine: StepEngine instance for executing steps.
            repo_root: Repository root path. Defaults to auto-detection.
            use_spec_bridge: If True, load flows from JSON specs.
            navigation_orchestrator: Optional NavigationOrchestrator for intelligent
                routing decisions. If not provided, creates a default one.
                Set to None explicitly to use envelope-first fallback routing.
        """
        self._engine = engine
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._flow_registry = FlowRegistry.get_instance()
        self._use_spec_bridge = use_spec_bridge
        self._spec_facade = SpecFacade(self._repo_root)
        self._lock = threading.Lock()

        # Navigation orchestrator for intelligent routing
        # Lazy import to avoid circular dependency
        if navigation_orchestrator is None:
            from swarm.runtime.navigator_integration import NavigationOrchestrator
            self._navigation_orchestrator: Optional["NavigationOrchestrator"] = NavigationOrchestrator(
                repo_root=self._repo_root
            )
        else:
            self._navigation_orchestrator = navigation_orchestrator

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
        run_state: Optional[RunState] = None,
        start_step: Optional[str] = None,
        end_step: Optional[str] = None,
    ) -> RunSummary:
        """Execute flow steps sequentially.

        Args:
            run_id: The run identifier.
            flow_key: The flow key.
            flow_def: The flow definition.
            spec: The run specification.
            resume: Whether resuming an existing run.
            run_state: Optional existing run state for resumption.
            start_step: Optional step ID to start from.
            end_step: Optional step ID to stop at.

        Returns:
            RunSummary with final status.
        """
        history: List[Dict[str, Any]] = []
        loop_state: Dict[str, int] = {}
        current_step_idx = 0
        steps = flow_def.steps

        # Use provided run_state or current_step_idx from start_step
        if run_state is not None:
            current_step_idx = run_state.step_index
        elif start_step is not None:
            for i, s in enumerate(steps):
                if s.id == start_step:
                    current_step_idx = i
                    break

        if not steps:
            return RunSummary(
                run_id=run_id,
                status=RunStatus.SUCCEEDED,
                sdlc_status=SDLCStatus.OK,
                flow_key=flow_key,
                completed_steps=[],
                duration_ms=0,
            )

        # Build FlowGraph for Navigator from flow definition
        flow_graph = self._build_flow_graph_from_definition(flow_def)

        # Use provided run_state or create new one for Navigator
        if run_state is None:
            run_state = RunState(
                run_id=run_id,
                flow_key=flow_key,
                current_step_id=steps[0].id if steps else None,
                step_index=current_step_idx,
                loop_state=loop_state,
                status="running",
            )

        # Track iteration count per step for stall detection
        iteration_counts: Dict[str, int] = {}

        while current_step_idx < len(steps):
            # Check for end_step boundary
            if end_step is not None:
                current_step = steps[current_step_idx]
                if current_step.id == end_step:
                    logger.info("Reached end_step %s, stopping execution", end_step)
                    break
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

            # Update RunState with current position
            run_state.current_step_id = step.id
            run_state.step_index = current_step_idx

            # Track iteration for this step
            iteration_counts[step.id] = iteration_counts.get(step.id, 0) + 1
            current_iteration = iteration_counts[step.id]

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

            # Mark node as completed in RunState
            run_state.mark_node_completed(step.id)

            run_base = self._repo_root / "swarm" / "runs" / run_id / flow_key

            # Use NavigationOrchestrator if available, otherwise fall back to envelope-first routing
            if self._navigation_orchestrator is not None:
                # Navigator-based routing
                next_step_id, reason, routing_source = self._route_via_navigator(
                    run_id=run_id,
                    flow_key=flow_key,
                    step=step,
                    step_result=step_result,
                    flow_graph=flow_graph,
                    run_state=run_state,
                    iteration=current_iteration,
                    spec=spec,
                    run_base=run_base,
                )
            else:
                # Fallback: envelope-first routing (legacy path)
                next_step_id, reason, routing_source = self._route_via_envelope_fallback(
                    run_id=run_id,
                    flow_key=flow_key,
                    step=step,
                    step_result=step_result,
                    flow_def=flow_def,
                    loop_state=loop_state,
                    run_base=run_base,
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
                        "routing_source": routing_source,
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

    def _build_flow_graph_from_definition(self, flow_def: FlowDefinition) -> FlowGraph:
        """Build a FlowGraph from FlowDefinition for Navigator context.

        Converts the flow_registry FlowDefinition to the router.FlowGraph
        format that NavigationOrchestrator expects.

        Args:
            flow_def: The flow definition from flow_registry.

        Returns:
            FlowGraph suitable for Navigator routing.
        """
        nodes: Dict[str, NodeConfig] = {}
        edges: List[Edge] = []

        for step in flow_def.steps:
            # Create node config
            node_config = NodeConfig(
                node_id=step.id,
                template_id=step.role or step.id,
                max_iterations=step.routing.max_iterations if step.routing else None,
            )
            nodes[step.id] = node_config

            # Create edges based on routing config
            if step.routing:
                # Add edge to next step
                if step.routing.next:
                    edges.append(Edge(
                        edge_id=f"{step.id}->{step.routing.next}",
                        from_node=step.id,
                        to_node=step.routing.next,
                        edge_type="sequence",
                        priority=50,
                    ))

                # Add loop edge if configured
                if step.routing.loop_target:
                    edges.append(Edge(
                        edge_id=f"{step.id}->{step.routing.loop_target}:loop",
                        from_node=step.id,
                        to_node=step.routing.loop_target,
                        edge_type="loop",
                        priority=40,
                    ))

        return FlowGraph(
            graph_id=flow_def.title or "flow",
            nodes=nodes,
            edges=edges,
            policy={"max_loop_iterations": 50},  # Safety fuse
        )

    def _route_via_navigator(
        self,
        run_id: RunId,
        flow_key: str,
        step: StepDefinition,
        step_result: Any,
        flow_graph: FlowGraph,
        run_state: RunState,
        iteration: int,
        spec: RunSpec,
        run_base: Path,
    ) -> Tuple[Optional[str], str, str]:
        """Route using NavigationOrchestrator.

        Calls NavigationOrchestrator.navigate() for intelligent routing decisions,
        including PAUSE->DETOUR rewriting and EXTEND_GRAPH support.

        Args:
            run_id: The run identifier.
            flow_key: The flow key.
            step: The current step definition.
            step_result: Result from step execution.
            flow_graph: The FlowGraph for edge candidates.
            run_state: Current run state (modified in place).
            iteration: Current iteration count for this step.
            spec: The run specification.
            run_base: Path to the run base directory.

        Returns:
            Tuple of (next_step_id, reason, routing_source).
        """
        # Build step result dict for Navigator
        step_result_dict = {
            "status": step_result.status,
            "output": step_result.output,
            "duration_ms": step_result.duration_ms,
        }

        # Get file changes from step result if available
        file_changes = None
        if hasattr(step_result, "file_changes"):
            file_changes = step_result.file_changes

        # Get verification result if available
        verification_result = None
        if hasattr(step_result, "verification_result"):
            verification_result = step_result.verification_result

        # Try to read previous envelope for context
        previous_envelope = None
        if step.id in run_state.handoff_envelopes:
            previous_envelope = run_state.handoff_envelopes[step.id]

        # Call NavigationOrchestrator.navigate()
        nav_result = self._navigation_orchestrator.navigate(
            run_id=run_id,
            flow_key=flow_key,
            current_node=step.id,
            iteration=iteration,
            flow_graph=flow_graph,
            step_result=step_result_dict,
            verification_result=verification_result,
            file_changes=file_changes,
            run_state=run_state,
            context_digest="",  # TODO: Implement context digest
            previous_envelope=previous_envelope,
            no_human_mid_flow=spec.no_human_mid_flow,
        )

        # Extract routing decision from NavigationResult
        next_step_id = nav_result.next_node
        routing_signal = nav_result.routing_signal

        reason = routing_signal.reason or "navigator_decision"
        routing_source = "navigator"

        # If detour was injected, note it in the reason
        if nav_result.detour_injected:
            routing_source = "navigator:detour"
            reason = f"Detour: {reason}"
        elif nav_result.extend_graph_injected:
            routing_source = "navigator:extend_graph"
            reason = f"Extend graph: {reason}"

        # Persist routing decision to envelope for consistency
        routing_dict = {
            "decision": routing_signal.decision.value if hasattr(routing_signal.decision, "value") else str(routing_signal.decision),
            "next_step_id": next_step_id,
            "reason": reason,
            "confidence": routing_signal.confidence,
            "needs_human": routing_signal.needs_human,
        }
        updated = update_envelope_routing(
            run_base=run_base,
            step_id=step.id,
            routing_signal=routing_dict,
        )
        if updated:
            logger.debug(
                "Navigator: Persisted routing to envelope for step %s: next=%s",
                step.id,
                next_step_id,
            )

        return next_step_id, reason, routing_source

    def _route_via_envelope_fallback(
        self,
        run_id: RunId,
        flow_key: str,
        step: StepDefinition,
        step_result: Any,
        flow_def: FlowDefinition,
        loop_state: Dict[str, int],
        run_base: Path,
    ) -> Tuple[Optional[str], str, str]:
        """Route using envelope-first fallback (legacy path).

        This is the original A3 envelope-first routing algorithm used when
        NavigationOrchestrator is not available.

        Args:
            run_id: The run identifier.
            flow_key: The flow key.
            step: The current step definition.
            step_result: Result from step execution.
            flow_def: The flow definition.
            loop_state: Microloop iteration state.
            run_base: Path to the run base directory.

        Returns:
            Tuple of (next_step_id, reason, routing_source).
        """
        # Try envelope-first routing
        envelope_routing = read_routing_from_envelope(run_base, step.id)
        routing_source = "envelope"

        if envelope_routing is not None:
            # Use routing from committed envelope (session mode path)
            decision_str = envelope_routing.get("decision", "advance")
            decision = parse_routing_decision(decision_str)

            if decision == RoutingDecision.TERMINATE:
                next_step_id = None
                reason = envelope_routing.get("reason", "terminate_via_envelope")
            elif decision == RoutingDecision.LOOP:
                # Handle loop: use loop_target from routing config
                routing = step.routing
                if routing and routing.loop_target:
                    loop_key = f"{step.id}:{routing.loop_target}"
                    current_iter = loop_state.get(loop_key, 0)
                    loop_state[loop_key] = current_iter + 1
                    next_step_id = routing.loop_target
                    reason = envelope_routing.get("reason", f"loop_via_envelope:{current_iter + 1}")
                else:
                    next_step_id = envelope_routing.get("next_step_id")
                    reason = envelope_routing.get("reason", "loop_via_envelope")
            else:
                # ADVANCE or BRANCH
                next_step_id = envelope_routing.get("next_step_id")
                reason = envelope_routing.get("reason", "advance_via_envelope")

                # If no next_step_id in envelope, fall back to routing config
                if next_step_id is None and step.routing and step.routing.next:
                    next_step_id = step.routing.next

            logger.debug(
                "A3: Using envelope routing for step %s: decision=%s, next=%s",
                step.id,
                decision_str,
                next_step_id,
            )
        else:
            # Fallback: receipt-based routing (legacy path)
            routing_source = "fallback"

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

            # Route to next step using legacy path
            next_step_id, reason = route_step(
                flow_def=flow_def,
                current_step=step,
                result=result_dict,
                loop_state=loop_state,
                run_id=run_id,
                flow_key=flow_key,
                receipt_reader=make_receipt_reader(),
            )

            # Persist routing decision to envelope for consistency
            routing_dict = {
                "decision": "terminate" if next_step_id is None else "advance",
                "next_step_id": next_step_id,
                "reason": reason,
                "confidence": 1.0,
                "needs_human": False,
            }
            updated = update_envelope_routing(
                run_base=run_base,
                step_id=step.id,
                routing_signal=routing_dict,
            )
            if updated:
                logger.debug(
                    "A3: Persisted fallback routing to envelope for step %s",
                    step.id,
                )

        return next_step_id, reason, routing_source


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
