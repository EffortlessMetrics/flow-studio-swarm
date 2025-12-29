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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from swarm.config.flow_registry import (
    FlowDefinition,
    FlowRegistry,
    StepDefinition,
)
from swarm.runtime import storage as storage_module
from swarm.runtime.engines import StepContext, StepEngine

# A3: Envelope-first routing imports
from swarm.runtime.handoff_io import (
    read_routing_from_envelope,
    update_envelope_routing,
)

# Macro navigation imports (between-flow routing)
from swarm.runtime.macro_navigator import (
    MacroNavigator,
    extract_flow_result,
)
from swarm.runtime.router import Edge, FlowGraph, NodeConfig  # For Navigator integration
from swarm.runtime.routing_utils import parse_routing_decision
from swarm.runtime.types import (
    FlowResult,
    InjectedNodeSpec,
    MacroAction,
    MacroRoutingDecision,
    RoutingDecision,
    RunEvent,
    RunId,
    RunPlanSpec,
    RunSpec,
    RunState,
    RunStatus,
    RunSummary,
    SDLCStatus,
    generate_run_id,
)

from .receipt_compat import read_receipt_field, update_receipt_routing
from .routing import build_routing_context, create_routing_signal
from .spec_facade import SpecFacade

if TYPE_CHECKING:
    from swarm.runtime.navigator_integration import NavigationOrchestrator
    from swarm.runtime.preflight import PreflightResult

logger = logging.getLogger(__name__)

# Maximum nested detour depth (prevents runaway sidequests)
MAX_DETOUR_DEPTH = 10


@dataclass
class FlowExecutionResult:
    """Result of a single flow execution including macro routing decision.

    Returned by run_stepwise_flow() when a MacroNavigator is provided,
    enabling callers to get routing guidance for the next flow.

    Attributes:
        run_id: The run identifier.
        summary: The RunSummary with execution details.
        macro_decision: Optional macro routing decision for next flow.
        flow_result: Optional structured flow result for routing context.
    """

    run_id: RunId
    summary: Optional["RunSummary"] = None
    macro_decision: Optional[MacroRoutingDecision] = None
    flow_result: Optional["FlowResult"] = None


@dataclass
class ResolvedNode:
    """Resolved execution context for a node.

    This is the unified representation for both regular flow nodes
    and dynamically injected nodes.

    Attributes:
        node_id: The node identifier.
        step_id: Step ID (same as node_id for compatibility).
        role: The role/station to execute.
        agents: List of agent keys to run.
        index: Position in flow (or -1 for injected nodes).
        is_injected: Whether this is a dynamically injected node.
        injected_spec: Full spec if this is an injected node.
        routing: Routing configuration if from flow definition.
    """

    node_id: str
    step_id: str
    role: str
    agents: Tuple[str, ...]
    index: int = -1
    is_injected: bool = False
    injected_spec: Optional[InjectedNodeSpec] = None
    routing: Optional[Any] = None  # StepRouting from flow_registry


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
        use_pack_specs: bool = False,
        navigation_orchestrator: Optional["NavigationOrchestrator"] = None,
        skip_preflight: bool = False,
    ):
        """Initialize the orchestrator.

        Args:
            engine: StepEngine instance for executing steps.
            repo_root: Repository root path. Defaults to auto-detection.
            use_spec_bridge: If True, load flows from JSON specs (legacy path).
            use_pack_specs: If True, load flows from pack JSON specs (new path).
                Takes precedence over use_spec_bridge when enabled.
            navigation_orchestrator: Optional NavigationOrchestrator for intelligent
                routing decisions. If not provided, creates a default one.
                Set to None explicitly to use envelope-first fallback routing.
            skip_preflight: If True, skip preflight environment checks.
                Useful for CI or when environment is known to be valid.
        """
        self._engine = engine
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._flow_registry = FlowRegistry.get_instance()
        self._use_spec_bridge = use_spec_bridge
        self._use_pack_specs = use_pack_specs
        self._spec_facade = SpecFacade(self._repo_root, use_pack_specs=use_pack_specs)
        self._lock = threading.Lock()
        self._skip_preflight = skip_preflight

        # Navigation orchestrator for intelligent routing
        # Lazy import to avoid circular dependency
        if navigation_orchestrator is None:
            from swarm.runtime.navigator_integration import NavigationOrchestrator

            self._navigation_orchestrator: Optional["NavigationOrchestrator"] = (
                NavigationOrchestrator(repo_root=self._repo_root)
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

    def _load_flow_definition(self, flow_key: str) -> Optional[FlowDefinition]:
        """Load flow definition from appropriate source.

        If use_pack_specs is enabled, loads from pack JSON specs.
        Otherwise falls back to the YAML-based flow registry.

        Args:
            flow_key: The flow to load (e.g., "build", "signal").

        Returns:
            FlowDefinition if found, None otherwise.
        """
        # Try pack specs first if enabled
        if self._use_pack_specs:
            flow_def = self._spec_facade.load_flow_definition(flow_key)
            if flow_def is not None:
                logger.debug("Loaded flow %s from pack specs", flow_key)
                return flow_def
            # Fall back to legacy if pack doesn't have it
            logger.debug("Flow %s not in pack, falling back to registry", flow_key)

        # Use legacy flow registry
        return self._flow_registry.get_flow(flow_key)

    def _run_preflight(
        self,
        run_id: RunId,
        spec: Optional[RunSpec],
        backend: str,
    ) -> "PreflightResult":
        """Run preflight environment checks before execution.

        Args:
            run_id: The run ID (for path checks).
            spec: The run specification.
            backend: Backend to check.

        Returns:
            PreflightResult with aggregate status.
        """
        from swarm.runtime.preflight import PreflightResult, run_preflight

        # Skip preflight if configured
        if self._skip_preflight:
            logger.debug("Preflight checks skipped (skip_preflight=True)")
            return PreflightResult(
                passed=True,
                warnings=["Preflight checks were skipped"],
                run_id=run_id,
                backend=backend,
            )

        # Run preflight checks
        result = run_preflight(
            run_spec=spec,
            backend=backend,
            run_id=run_id,
            repo_root=self._repo_root,
            skip_preflight=False,
        )

        # Log preflight result
        if result.passed:
            logger.info(
                "Preflight passed (%d checks, %d warnings) in %dms",
                len(result.checks),
                len(result.warnings),
                result.total_duration_ms,
            )
        else:
            logger.warning(
                "Preflight failed with %d blocking issue(s): %s",
                len(result.blocking_issues),
                "; ".join(result.blocking_issues[:3]),  # First 3 issues
            )

        # Emit preflight event
        storage_module.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=datetime.now(timezone.utc),
                kind="preflight_completed",
                flow_key="",
                step_id=None,
                payload={
                    "passed": result.passed,
                    "blocking_issues": result.blocking_issues,
                    "warnings": result.warnings,
                    "duration_ms": result.total_duration_ms,
                    "checks": [{"name": c.name, "status": c.status.value} for c in result.checks],
                },
            ),
        )

        return result

    def run_stepwise_flow(
        self,
        flow_key: str,
        spec: RunSpec,
        resume: bool = False,
        run_id: Optional[RunId] = None,
        macro_navigator: Optional[MacroNavigator] = None,
    ) -> RunId:
        """Execute a flow step by step.

        Args:
            flow_key: The flow to execute (e.g., "build", "plan").
            spec: The run specification.
            resume: Whether to resume an existing run.
            run_id: Optional run ID for resuming.
            macro_navigator: Optional MacroNavigator for between-flow routing.
                If provided, the flow result and routing decision will be
                computed at flow completion.

        Returns:
            The run ID.

        Note:
            For full macro routing support with flow result and decision,
            use run_stepwise_flow_with_routing() instead.
        """
        result = self.run_stepwise_flow_with_routing(
            flow_key=flow_key,
            spec=spec,
            resume=resume,
            run_id=run_id,
            macro_navigator=macro_navigator,
        )
        return result.run_id

    def run_stepwise_flow_with_routing(
        self,
        flow_key: str,
        spec: RunSpec,
        resume: bool = False,
        run_id: Optional[RunId] = None,
        macro_navigator: Optional[MacroNavigator] = None,
        run_state: Optional[RunState] = None,
    ) -> FlowExecutionResult:
        """Execute a flow step by step with macro routing support.

        This is the full-featured version of run_stepwise_flow() that returns
        a FlowExecutionResult with the macro routing decision for the next flow.

        Args:
            flow_key: The flow to execute (e.g., "build", "plan").
            spec: The run specification.
            resume: Whether to resume an existing run.
            run_id: Optional run ID for resuming.
            macro_navigator: Optional MacroNavigator for between-flow routing.
                If provided, route_after_flow() is called at flow completion.
            run_state: Optional existing RunState for resumption or tracking.

        Returns:
            FlowExecutionResult with run_id, summary, and optional macro_decision.

        Example:
            # Run a single flow with macro routing
            navigator = create_default_navigator()
            result = orchestrator.run_stepwise_flow_with_routing(
                flow_key="build",
                spec=RunSpec(flow_keys=["build"], initiator="cli"),
                macro_navigator=navigator,
            )

            # Check the routing decision
            if result.macro_decision:
                if result.macro_decision.action == MacroAction.ADVANCE:
                    next_flow = result.macro_decision.next_flow
                elif result.macro_decision.action == MacroAction.PAUSE:
                    # Wait for human intervention
                    pass
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

        # Run preflight checks before expensive work
        backend = spec.backend if spec else "claude-harness"
        preflight_result = self._run_preflight(run_id, spec, backend)
        if not preflight_result.passed:
            # Preflight failed - attempt to inject env-doctor sidequest or halt
            # For now, create a temporary run_state for potential sidequest injection
            temp_run_state = RunState(run_id=run_id, flow_key=flow_key, status="pending")

            from swarm.runtime.preflight import inject_env_doctor_sidequest

            if inject_env_doctor_sidequest(temp_run_state, preflight_result):
                logger.info("Preflight failed but env-doctor sidequest injected")
                # Continue with the sidequest handling
                if run_state is None:
                    run_state = temp_run_state
                else:
                    # Copy injected nodes to provided run_state
                    for node_id, node_spec in temp_run_state.injected_node_specs.items():
                        run_state.register_injected_node(node_spec)
            else:
                # No sidequest available - halt with clear error
                error_msg = (
                    f"Preflight failed with {len(preflight_result.blocking_issues)} blocking issue(s): "
                    f"{'; '.join(preflight_result.blocking_issues)}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        # Load flow definition - use pack specs if enabled
        flow_def = self._load_flow_definition(flow_key)
        if flow_def is None:
            raise ValueError(f"Unknown flow: {flow_key}")

        # Create run directory and initial state
        storage_module.init_run(run_id, flow_key, spec)

        # Use provided run_state or create new one
        if run_state is None:
            run_state = RunState(
                run_id=run_id,
                flow_key=flow_key,
                status="running",
            )

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
                run_id, flow_key, flow_def, spec, resume=resume, run_state=run_state
            )

            # Perform macro routing if navigator provided
            macro_decision: Optional[MacroRoutingDecision] = None
            flow_result: Optional[FlowResult] = None

            if macro_navigator is not None:
                # Extract flow result for routing decision
                artifacts_base = self._repo_root / "swarm" / "runs" / run_id
                flow_result = extract_flow_result(
                    flow_key=flow_key,
                    run_state=run_state,
                    artifacts_base=artifacts_base,
                )

                # Get macro routing decision
                macro_decision = macro_navigator.route_after_flow(
                    completed_flow=flow_key,
                    flow_result=flow_result,
                    run_state=run_state,
                )

                # Log the macro routing decision
                logger.info(
                    "MacroNavigator: Flow '%s' completed -> %s (next: %s, reason: %s)",
                    flow_key,
                    macro_decision.action.value,
                    macro_decision.next_flow or "(none)",
                    macro_decision.reason,
                )

                # Emit macro_route event for audit trail
                storage_module.append_event(
                    run_id,
                    RunEvent(
                        run_id=run_id,
                        ts=datetime.now(timezone.utc),
                        kind="macro_route",
                        flow_key=flow_key,
                        step_id=None,
                        payload={
                            "action": macro_decision.action.value,
                            "next_flow": macro_decision.next_flow,
                            "reason": macro_decision.reason,
                            "rule_applied": macro_decision.rule_applied,
                            "confidence": macro_decision.confidence,
                        },
                    ),
                )

                # Update run_state with the routing decision for audit trail
                run_state.flow_transition_history.append(
                    {
                        "from_flow": flow_key,
                        "to_flow": macro_decision.next_flow,
                        "action": macro_decision.action.value,
                        "reason": macro_decision.reason,
                        "rule_applied": macro_decision.rule_applied,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

                # Handle PAUSE case - update run state status
                if macro_decision.action == MacroAction.PAUSE:
                    run_state.status = "paused"
                    logger.info(
                        "MacroNavigator: PAUSE requested - stopping execution for human intervention. Reason: %s",
                        macro_decision.reason,
                    )
                    storage_module.append_event(
                        run_id,
                        RunEvent(
                            run_id=run_id,
                            ts=datetime.now(timezone.utc),
                            kind="flow_paused",
                            flow_key=flow_key,
                            step_id=None,
                            payload={
                                "reason": macro_decision.reason,
                                "awaiting_human": True,
                            },
                        ),
                    )

            return FlowExecutionResult(
                run_id=run_id,
                summary=summary,
                macro_decision=macro_decision,
                flow_result=flow_result,
            )

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

    def run_autopilot(
        self,
        spec: RunSpec,
        plan_id: Optional[str] = None,
        run_plan: Optional[RunPlanSpec] = None,
        run_id: Optional[RunId] = None,
    ) -> RunId:
        """Execute multiple flows in autopilot mode using MacroNavigator.

        This method orchestrates the full SDLC by:
        1. Loading the run plan (flow sequence + policies)
        2. Executing flows sequentially
        3. Using MacroNavigator for between-flow routing
        4. Handling bounces, retries, and termination

        Args:
            spec: The run specification.
            plan_id: ID of a stored run plan to use.
            run_plan: Explicit RunPlanSpec (overrides plan_id).
            run_id: Optional run ID (generates if not provided).

        Returns:
            The run ID.

        Example:
            # Run full SDLC with autopilot
            run_id = orchestrator.run_autopilot(
                spec=RunSpec(flow_keys=["signal"], initiator="cli"),
                plan_id="default-autopilot",
            )
        """
        # Generate run ID
        if run_id is None:
            run_id = generate_run_id()

        # Load run plan - use explicit plan, or create default
        if run_plan is None:
            # Note: load_run_plan would be implemented in run_plan_api module
            # For now, we always use default if no explicit plan provided
            run_plan = RunPlanSpec.default()

        # Create MacroNavigator
        macro_nav = MacroNavigator(run_plan)

        # Initialize stop tracking
        with self._lock:
            if run_id not in self._stop_requests:
                self._stop_requests[run_id] = threading.Event()

        # Emit run_started event
        storage_module.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=datetime.now(timezone.utc),
                kind="autopilot_started",
                flow_key="",
                step_id=None,
                payload={
                    "plan_id": plan_id,
                    "flow_sequence": run_plan.flow_sequence,
                    "human_policy": run_plan.human_policy.mode,
                },
            ),
        )

        # Track overall run state
        artifacts_base = self._repo_root / "swarm" / "runs" / run_id
        current_flow_idx = 0

        # Create a shared run state for macro-level tracking
        run_state = RunState(
            run_id=run_id,
            flow_key=run_plan.flow_sequence[0] if run_plan.flow_sequence else "",
            status="running",
        )

        try:
            while current_flow_idx < len(run_plan.flow_sequence):
                # Check for stop request
                if self._is_stop_requested(run_id):
                    logger.info("Stop requested, pausing autopilot at flow %d", current_flow_idx)
                    storage_module.append_event(
                        run_id,
                        RunEvent(
                            run_id=run_id,
                            ts=datetime.now(timezone.utc),
                            kind="autopilot_stopped",
                            flow_key=run_plan.flow_sequence[current_flow_idx],
                            step_id=None,
                            payload={"flow_index": current_flow_idx},
                        ),
                    )
                    break

                flow_key = run_plan.flow_sequence[current_flow_idx]
                run_state.flow_key = flow_key
                run_state.current_flow_index = current_flow_idx + 1  # 1-indexed for display

                logger.info(
                    "Autopilot: Starting flow %d/%d: %s",
                    current_flow_idx + 1,
                    len(run_plan.flow_sequence),
                    flow_key,
                )

                # Get flow definition - use pack specs if enabled
                flow_def = self._load_flow_definition(flow_key)
                if flow_def is None:
                    logger.error("Unknown flow in sequence: %s", flow_key)
                    break

                # Create run directory for this flow
                storage_module.init_run(run_id, flow_key, spec)

                # Emit flow_started event
                storage_module.append_event(
                    run_id,
                    RunEvent(
                        run_id=run_id,
                        ts=datetime.now(timezone.utc),
                        kind="flow_started",
                        flow_key=flow_key,
                        step_id=None,
                        payload={"flow_index": current_flow_idx},
                    ),
                )

                # Execute the flow
                try:
                    self._execute_stepwise(
                        run_id=run_id,
                        flow_key=flow_key,
                        flow_def=flow_def,
                        spec=spec,
                        run_state=run_state,
                    )
                except Exception as e:
                    logger.error("Flow %s failed: %s", flow_key, e)
                    storage_module.append_event(
                        run_id,
                        RunEvent(
                            run_id=run_id,
                            ts=datetime.now(timezone.utc),
                            kind="flow_failed",
                            flow_key=flow_key,
                            step_id=None,
                            payload={"error": str(e)},
                        ),
                    )
                    break

                # Extract flow result for MacroNavigator
                flow_result = extract_flow_result(
                    flow_key=flow_key,
                    run_state=run_state,
                    artifacts_base=artifacts_base,
                )

                # Get macro routing decision
                macro_decision = macro_nav.route_after_flow(
                    completed_flow=flow_key,
                    flow_result=flow_result,
                    run_state=run_state,
                )

                # Emit macro routing event
                storage_module.append_event(
                    run_id,
                    RunEvent(
                        run_id=run_id,
                        ts=datetime.now(timezone.utc),
                        kind="macro_route",
                        flow_key=flow_key,
                        step_id=None,
                        payload={
                            "action": macro_decision.action.value,
                            "next_flow": macro_decision.next_flow,
                            "reason": macro_decision.reason,
                            "rule_applied": macro_decision.rule_applied,
                        },
                    ),
                )

                # Apply the decision
                if macro_decision.action == MacroAction.TERMINATE:
                    logger.info("Autopilot: Terminating - %s", macro_decision.reason)
                    break

                elif macro_decision.action == MacroAction.PAUSE:
                    logger.info("Autopilot: Pausing for human - %s", macro_decision.reason)
                    storage_module.append_event(
                        run_id,
                        RunEvent(
                            run_id=run_id,
                            ts=datetime.now(timezone.utc),
                            kind="autopilot_paused",
                            flow_key=flow_key,
                            step_id=None,
                            payload={"reason": macro_decision.reason},
                        ),
                    )
                    break

                elif macro_decision.action == MacroAction.GOTO:
                    # Jump to a specific flow (e.g., bounce from gate to build)
                    target_flow = macro_decision.next_flow
                    if target_flow:
                        try:
                            target_idx = run_plan.flow_sequence.index(target_flow)
                            current_flow_idx = target_idx
                            logger.info("Autopilot: GOTO %s (index %d)", target_flow, target_idx)

                            # Record flow transition
                            run_state.flow_transition_history.append(
                                {
                                    "from_flow": flow_key,
                                    "to_flow": target_flow,
                                    "action": "goto",
                                    "reason": macro_decision.reason,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            )
                        except ValueError:
                            logger.error("GOTO target %s not in sequence", target_flow)
                            break
                    else:
                        logger.error("GOTO action without target flow")
                        break

                elif macro_decision.action == MacroAction.REPEAT:
                    # Re-run the same flow
                    logger.info("Autopilot: REPEAT %s", flow_key)
                    run_state.flow_transition_history.append(
                        {
                            "from_flow": flow_key,
                            "to_flow": flow_key,
                            "action": "repeat",
                            "reason": macro_decision.reason,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    # Don't increment current_flow_idx

                elif macro_decision.action == MacroAction.SKIP:
                    # Skip to next flow
                    current_flow_idx += 1
                    logger.info("Autopilot: SKIP to flow %d", current_flow_idx)

                else:  # ADVANCE
                    # Normal advancement to next flow
                    current_flow_idx += 1
                    if current_flow_idx < len(run_plan.flow_sequence):
                        next_flow = run_plan.flow_sequence[current_flow_idx]
                        run_state.flow_transition_history.append(
                            {
                                "from_flow": flow_key,
                                "to_flow": next_flow,
                                "action": "advance",
                                "reason": macro_decision.reason,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )

            # Emit autopilot_completed event
            storage_module.append_event(
                run_id,
                RunEvent(
                    run_id=run_id,
                    ts=datetime.now(timezone.utc),
                    kind="autopilot_completed",
                    flow_key="",
                    step_id=None,
                    payload={
                        "flows_executed": current_flow_idx,
                        "total_flows": len(run_plan.flow_sequence),
                        "routing_history": macro_nav.get_routing_history(),
                    },
                ),
            )

            return run_id

        except Exception as e:
            logger.error("Autopilot run %s failed: %s", run_id, e)
            storage_module.append_event(
                run_id,
                RunEvent(
                    run_id=run_id,
                    ts=datetime.now(timezone.utc),
                    kind="autopilot_failed",
                    flow_key="",
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

            # For injected nodes, resolve via the node resolver
            current_node_id = run_state.current_step_id or step.id
            resolved = self._resolve_node(current_node_id, flow_def, run_state)

            # If we resolved to an injected node, use its details
            if resolved and resolved.is_injected:
                # Create a synthetic step context for the injected node
                step_role = resolved.role
                step_agents = resolved.agents
            else:
                step_role = step.role
                step_agents = tuple(step.agents) if step.agents else ()

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
                step_id=current_node_id,  # Use current_node_id instead of step.id
                step_index=resolved.index if resolved else step.index,
                total_steps=len(steps),
                spec=spec,
                flow_title=flow_def.title,
                step_role=step_role,  # Use resolved role
                step_agents=step_agents,  # Use resolved agents
                history=history,
                routing=routing_ctx,
            )

            # Execute step
            step_result, events = self._engine.run_step(ctx)

            # Persist events
            for event in events:
                storage_module.append_event(run_id, event)

            # Add to history
            history.append(
                {
                    "step_id": step.id,
                    "status": step_result.status,
                    "output": step_result.output,
                    "duration_ms": step_result.duration_ms,
                }
            )

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
                    edges.append(
                        Edge(
                            edge_id=f"{step.id}->{step.routing.next}",
                            from_node=step.id,
                            to_node=step.routing.next,
                            edge_type="sequence",
                            priority=50,
                        )
                    )

                # Add loop edge if configured
                if step.routing.loop_target:
                    edges.append(
                        Edge(
                            edge_id=f"{step.id}->{step.routing.loop_target}:loop",
                            from_node=step.id,
                            to_node=step.routing.loop_target,
                            edge_type="loop",
                            priority=40,
                        )
                    )

        return FlowGraph(
            graph_id=flow_def.title or "flow",
            nodes=nodes,
            edges=edges,
            policy={"max_loop_iterations": 50},  # Safety fuse
        )

    def _resolve_node(
        self,
        node_id: str,
        flow_def: FlowDefinition,
        run_state: RunState,
    ) -> Optional[ResolvedNode]:
        """Resolve a node_id to an executable ResolvedNode.

        This method handles both:
        1. Regular flow graph nodes (from FlowDefinition)
        2. Dynamically injected nodes (from run_state.injected_node_specs)

        Injected nodes take precedence - if a node_id exists in both
        the flow and as an injected node, the injected version is used.

        Args:
            node_id: The node ID to resolve.
            flow_def: The flow definition containing regular steps.
            run_state: RunState containing injected node specs.

        Returns:
            ResolvedNode if found, None otherwise.
        """
        # First, check injected nodes (they take precedence)
        injected_spec = run_state.get_injected_node_spec(node_id)
        if injected_spec is not None:
            return ResolvedNode(
                node_id=node_id,
                step_id=node_id,
                role=injected_spec.station_id,
                agents=(injected_spec.agent_key or injected_spec.station_id,),
                index=-1,  # Injected nodes don't have a flow index
                is_injected=True,
                injected_spec=injected_spec,
                routing=None,
            )

        # Then check regular flow steps
        for step in flow_def.steps:
            if step.id == node_id:
                return ResolvedNode(
                    node_id=node_id,
                    step_id=step.id,
                    role=step.role or step.id,
                    agents=tuple(step.agents) if step.agents else (),
                    index=step.index,
                    is_injected=False,
                    injected_spec=None,
                    routing=step.routing,
                )

        # Node not found
        logger.warning("Could not resolve node_id: %s", node_id)
        return None

    def _get_next_node_id(
        self,
        current_node_id: str,
        nav_result_node: Optional[str],
        flow_def: FlowDefinition,
        run_state: RunState,
    ) -> Optional[str]:
        """Determine the next node_id to execute.

        Priority order:
        1. Navigator-provided next node (if valid)
        2. Resume from interruption stack (if sidequest complete)
        3. Sequential next step in flow
        4. None (flow complete)

        Args:
            current_node_id: The current node that just executed.
            nav_result_node: Navigator's suggested next node.
            flow_def: The flow definition.
            run_state: Current run state.

        Returns:
            Next node_id to execute, or None if flow is complete.
        """
        # If navigator provided a target, validate and use it
        if nav_result_node:
            resolved = self._resolve_node(nav_result_node, flow_def, run_state)
            if resolved is not None:
                return nav_result_node
            else:
                logger.warning(
                    "Navigator target %s could not be resolved, falling back",
                    nav_result_node,
                )

        # Check if we're resuming from a sidequest
        if run_state.peek_resume() is not None:
            # There's a resume point - sidequest handling will pop it
            # This is handled by check_and_handle_detour_completion in navigate()
            pass

        # For injected nodes, check if there's a next in sequence
        if current_node_id.startswith("sq-"):
            # This is a sidequest node - next node determined by sidequest cursor
            # The navigate() call handles this via check_and_handle_detour_completion
            return None

        # For regular nodes, find sequential next
        current_idx = None
        for i, step in enumerate(flow_def.steps):
            if step.id == current_node_id:
                current_idx = i
                break

        if current_idx is not None and current_idx + 1 < len(flow_def.steps):
            return flow_def.steps[current_idx + 1].id

        # No next step - flow complete
        return None

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
            "decision": routing_signal.decision.value
            if hasattr(routing_signal.decision, "value")
            else str(routing_signal.decision),
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
            # Fallback: Use create_routing_signal for proper decision semantics
            routing_source = "fallback"

            result_dict = {
                "run_id": run_id,
                "flow_key": flow_key,
                "status": step_result.status,
            }

            # Create receipt reader for routing
            def make_receipt_reader():
                repo_root = self._repo_root
                return lambda r, f, s, a, field: read_receipt_field(repo_root, r, f, s, a, field)

            # Create a proper RoutingSignal using create_routing_signal
            # This preserves LOOP/BRANCH/ADVANCE/TERMINATE semantics
            routing_signal = create_routing_signal(
                step=step,
                result=result_dict,
                loop_state=loop_state,
                receipt_reader=make_receipt_reader(),
            )

            # Extract next_step_id and reason from the signal
            next_step_id = routing_signal.next_step_id
            reason = routing_signal.reason or "fallback_routing"

            # Handle loop state updates for LOOP decisions
            if routing_signal.decision == RoutingDecision.LOOP:
                routing = step.routing
                if routing and routing.loop_target:
                    loop_key = f"{step.id}:{routing.loop_target}"
                    current_iter = loop_state.get(loop_key, 0)
                    loop_state[loop_key] = current_iter + 1
                    next_step_id = routing.loop_target
                    reason = f"loop_via_fallback:{current_iter + 1}"

            # Persist routing decision to envelope for consistency
            # Use the proper decision from the RoutingSignal
            routing_dict = {
                "decision": routing_signal.decision.value
                if hasattr(routing_signal.decision, "value")
                else str(routing_signal.decision),
                "next_step_id": next_step_id,
                "reason": reason,
                "confidence": routing_signal.confidence,
                "needs_human": routing_signal.needs_human,
                "loop_count": routing_signal.loop_count,
                "exit_condition_met": routing_signal.exit_condition_met,
            }
            updated = update_envelope_routing(
                run_base=run_base,
                step_id=step.id,
                routing_signal=routing_dict,
            )
            if updated:
                logger.debug(
                    "A3: Persisted fallback routing to envelope for step %s (decision=%s)",
                    step.id,
                    routing_dict["decision"],
                )

        return next_step_id, reason, routing_source


# Backwards compatibility alias
GeminiStepOrchestrator = StepwiseOrchestrator


def get_orchestrator(
    engine: Optional[StepEngine] = None,
    repo_root: Optional[Path] = None,
    use_pack_specs: bool = False,
    skip_preflight: bool = False,
) -> StepwiseOrchestrator:
    """Factory function to create a stepwise orchestrator.

    Args:
        engine: Optional StepEngine instance. Creates GeminiStepEngine if None.
        repo_root: Optional repository root path.
        use_pack_specs: If True, use pack JSON specs instead of YAML registry.
        skip_preflight: If True, skip preflight environment checks.
            Useful for CI or when environment is known to be valid.

    Returns:
        Configured StepwiseOrchestrator instance.
    """
    from swarm.runtime.engines import GeminiStepEngine

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]

    if engine is None:
        engine = GeminiStepEngine(repo_root)

    return StepwiseOrchestrator(
        engine=engine,
        repo_root=repo_root,
        use_pack_specs=use_pack_specs,
        skip_preflight=skip_preflight,
    )


__all__ = [
    "FlowExecutionResult",
    "ResolvedNode",
    "StepwiseOrchestrator",
    "GeminiStepOrchestrator",
    "get_orchestrator",
]
