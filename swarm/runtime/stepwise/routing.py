"""
routing.py - Fallback routing logic for stepwise execution.

This module provides the routing decision logic that determines the next step
after each step execution. It supports:

1. Spec-first routing: Uses FlowSpec from swarm/spec/flows/
2. Config-based routing: Falls back to YAML config from flow_registry
3. HandoffEnvelope routing: Uses RoutingSignal from step finalization

Routing Kinds:
- linear: Simple sequential flow to next step
- microloop: Loops back until condition is met or max iterations reached
- branch: Routes based on step result status
- terminal: Ends the flow

The routing module is stateless - loop state and receipt reading are passed in.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, TYPE_CHECKING

from swarm.config.flow_registry import FlowDefinition, StepDefinition
from swarm.runtime.types import (
    HandoffEnvelope,
    RoutingDecision,
    RoutingSignal,
)

if TYPE_CHECKING:
    from swarm.runtime.engines.models import RoutingContext

logger = logging.getLogger(__name__)


# Type for receipt field reader function
ReceiptReader = Callable[[str, str, str, str, str], Optional[str]]


def create_routing_signal(
    step: StepDefinition,
    result: Dict[str, Any],
    loop_state: Dict[str, int],
    receipt_reader: Optional[ReceiptReader] = None,
    spec_routing: Optional[Dict[str, Any]] = None,
    spec_exit_on: Optional[Dict[str, Any]] = None,
) -> RoutingSignal:
    """Create a RoutingSignal from step result and routing config.

    Uses spec-first routing when spec_routing is available, otherwise
    falls back to config-based routing from step.routing.

    Args:
        step: The step that was executed.
        result: The step execution result dictionary.
        loop_state: Dictionary tracking iteration counts per microloop.
        receipt_reader: Optional function to read receipt fields.
            Signature: (run_id, flow_key, step_id, agent_key, field_name) -> Optional[str]
        spec_routing: Optional routing config from FlowSpec.
        spec_exit_on: Optional exit_on conditions from FlowSpec.

    Returns:
        A RoutingSignal with the routing decision.
    """
    # Use spec-first if available
    if spec_routing:
        return _create_routing_signal_from_spec(
            step, result, loop_state, spec_routing, spec_exit_on, receipt_reader
        )

    # Fall back to config-based routing
    return _create_routing_signal_from_config(
        step, result, loop_state, receipt_reader
    )


def _create_routing_signal_from_config(
    step: StepDefinition,
    result: Dict[str, Any],
    loop_state: Dict[str, int],
    receipt_reader: Optional[ReceiptReader] = None,
) -> RoutingSignal:
    """Create a RoutingSignal using config-based routing.

    Args:
        step: The step that was executed.
        result: The step execution result dictionary.
        loop_state: Dictionary tracking iteration counts.
        receipt_reader: Optional function to read receipt fields.

    Returns:
        A RoutingSignal with the routing decision.
    """
    routing = step.routing

    # Default values
    decision = RoutingDecision.ADVANCE
    next_step_id = None
    reason = "step_complete"
    confidence = 1.0
    needs_human = False

    if routing is None:
        # No routing config: fall back to linear progression
        # Find next step by index using flow_def from step
        if hasattr(step, "flow_def") and step.flow_def:
            for s in step.flow_def.steps:
                if s.index == step.index + 1:
                    next_step_id = s.id
                    reason = "linear_default"
                    break
        if next_step_id is None:
            decision = RoutingDecision.TERMINATE
            reason = "flow_complete_no_routing"

    elif routing.kind == "linear":
        if routing.next:
            next_step_id = routing.next
            reason = "linear_explicit"
        else:
            decision = RoutingDecision.TERMINATE
            reason = "flow_complete_linear"

    elif routing.kind == "microloop":
        result_signal = _handle_microloop_routing(
            step, result, loop_state, routing, receipt_reader
        )
        return result_signal

    elif routing.kind == "branch":
        # Branch routing based on result values
        if routing.branches and result.get("status"):
            branch_key = result.get("status")
            if branch_key in routing.branches:
                next_step_id = routing.branches[branch_key]
                reason = f"branch:{branch_key}"

        # Fallback to next
        if next_step_id is None and routing.next:
            next_step_id = routing.next
            reason = "branch_fallback"

    return RoutingSignal(
        decision=decision,
        next_step_id=next_step_id,
        reason=reason,
        confidence=confidence,
        needs_human=needs_human,
    )


def _handle_microloop_routing(
    step: StepDefinition,
    result: Dict[str, Any],
    loop_state: Dict[str, int],
    routing: Any,  # StepRouting
    receipt_reader: Optional[ReceiptReader] = None,
) -> RoutingSignal:
    """Handle microloop routing logic.

    Args:
        step: The step that was executed.
        result: The step execution result dictionary.
        loop_state: Dictionary tracking iteration counts.
        routing: The step's routing configuration.
        receipt_reader: Optional function to read receipt fields.

    Returns:
        RoutingSignal for the microloop.
    """
    decision = RoutingDecision.ADVANCE
    next_step_id = None
    reason = "step_complete"

    # Check loop iteration count
    loop_key = f"{step.id}:{routing.loop_target}"
    current_iter = loop_state.get(loop_key, 0)

    # Safety check: max iterations
    if current_iter >= routing.max_iterations:
        if routing.next:
            next_step_id = routing.next
            reason = f"max_iterations_reached:{routing.max_iterations}"
        else:
            decision = RoutingDecision.TERMINATE
            reason = f"flow_complete_max_iterations:{routing.max_iterations}"
        return RoutingSignal(
            decision=decision,
            next_step_id=next_step_id,
            reason=reason,
            confidence=1.0,
            needs_human=False,
        )

    # Check loop condition from receipt
    if routing.loop_condition_field and receipt_reader:
        agent_key = step.agents[0] if step.agents else "unknown"
        run_id = result.get("run_id", "")
        flow_key = result.get("flow_key", "")

        field_value = receipt_reader(
            run_id, flow_key, step.id, agent_key, routing.loop_condition_field
        )

        if field_value and field_value in routing.loop_success_values:
            # Condition met, exit loop
            if routing.next:
                next_step_id = routing.next
                reason = f"loop_exit_condition_met:{field_value}"
            else:
                decision = RoutingDecision.TERMINATE
                reason = f"flow_complete_condition_met:{field_value}"
            return RoutingSignal(
                decision=decision,
                next_step_id=next_step_id,
                reason=reason,
                confidence=1.0,
                needs_human=False,
            )

        # Check can_further_iteration_help field as fallback
        can_iterate = receipt_reader(
            run_id, flow_key, step.id, agent_key, "can_further_iteration_help"
        )
        if can_iterate and can_iterate.lower() == "no":
            # Critic says no further iteration will help
            if routing.next:
                next_step_id = routing.next
                reason = "loop_exit_no_further_help"
            else:
                decision = RoutingDecision.TERMINATE
                reason = "flow_complete_no_further_help"
            return RoutingSignal(
                decision=decision,
                next_step_id=next_step_id,
                reason=reason,
                confidence=1.0,
                needs_human=False,
            )

    # Loop back to target
    if routing.loop_target:
        next_step_id = routing.loop_target
        reason = f"loop_iteration:{current_iter + 1}"
        decision = RoutingDecision.LOOP

    return RoutingSignal(
        decision=decision,
        next_step_id=next_step_id,
        reason=reason,
        confidence=1.0,
        needs_human=False,
    )


def _create_routing_signal_from_spec(
    step: StepDefinition,
    result: Dict[str, Any],
    loop_state: Dict[str, int],
    spec_routing: Dict[str, Any],
    spec_exit_on: Optional[Dict[str, Any]] = None,
    receipt_reader: Optional[ReceiptReader] = None,
) -> RoutingSignal:
    """Create a RoutingSignal using FlowSpec routing configuration.

    Supports routing kinds: linear, microloop, branch, terminal.
    Supports exit_on conditions for microloops.

    Args:
        step: The step that was executed.
        result: The step execution result dictionary.
        loop_state: Dictionary tracking iteration counts per microloop.
        spec_routing: Routing configuration from FlowSpec.
        spec_exit_on: Optional exit_on conditions from FlowSpec.
        receipt_reader: Optional function to read receipt fields.

    Returns:
        A RoutingSignal with the routing decision.
    """
    kind = spec_routing.get("kind", "linear")
    decision = RoutingDecision.ADVANCE
    next_step_id = None
    reason = "step_complete"
    confidence = 1.0
    needs_human = False
    loop_count = 0
    exit_condition_met = False

    if kind == "terminal":
        return RoutingSignal(
            decision=RoutingDecision.TERMINATE,
            next_step_id=None,
            reason="terminal_step",
            confidence=confidence,
            needs_human=needs_human,
        )

    elif kind == "linear":
        next_step_id = spec_routing.get("next")
        if next_step_id:
            reason = "linear_via_spec"
        else:
            decision = RoutingDecision.TERMINATE
            reason = "flow_complete_via_spec"

    elif kind == "microloop":
        loop_target = spec_routing.get("loop_target")
        next_after_loop = spec_routing.get("next")
        max_iterations = spec_routing.get("max_iterations", 3)

        loop_key = f"{step.id}:{loop_target}" if loop_target else step.id
        current_iter = loop_state.get(loop_key, 0)
        loop_count = current_iter

        # Check exit_on conditions from FlowSpec
        if spec_exit_on:
            # Check status condition
            status_values = spec_exit_on.get("status", [])
            step_status = result.get("status", "")
            if status_values and step_status in status_values:
                exit_condition_met = True
                reason = f"exit_on_status:{step_status}"

            # Check can_further_iteration_help condition
            if spec_exit_on.get("can_further_iteration_help") is False and receipt_reader:
                agent_key = step.agents[0] if step.agents else "unknown"
                run_id = result.get("run_id", "")
                flow_key = result.get("flow_key", "")

                can_iterate = receipt_reader(
                    run_id, flow_key, step.id, agent_key, "can_further_iteration_help"
                )
                if can_iterate and can_iterate.lower() == "no":
                    exit_condition_met = True
                    reason = "exit_on_no_further_help"

        # Check max iterations
        if current_iter >= max_iterations:
            exit_condition_met = True
            reason = f"max_iterations_reached:{max_iterations}"

        if exit_condition_met:
            if next_after_loop:
                next_step_id = next_after_loop
                decision = RoutingDecision.ADVANCE
            else:
                decision = RoutingDecision.TERMINATE
        else:
            # Loop back
            if loop_target:
                next_step_id = loop_target
                decision = RoutingDecision.LOOP
                reason = f"loop_iteration:{current_iter + 1}"

    elif kind == "branch":
        branches = spec_routing.get("branches", {})
        step_status = result.get("status", "")

        if branches and step_status in branches:
            next_step_id = branches[step_status]
            reason = f"branch_via_spec:{step_status}"
            decision = RoutingDecision.BRANCH
        else:
            # Default/fallback
            next_step_id = spec_routing.get("next")
            if next_step_id:
                reason = "branch_default_via_spec"
            else:
                decision = RoutingDecision.TERMINATE
                reason = "flow_complete_branch_via_spec"

    return RoutingSignal(
        decision=decision,
        next_step_id=next_step_id,
        reason=reason,
        confidence=confidence,
        needs_human=needs_human,
        loop_count=loop_count,
        exit_condition_met=exit_condition_met,
    )


def route_step(
    flow_def: FlowDefinition,
    current_step: StepDefinition,
    result: Dict[str, Any],
    loop_state: Dict[str, int],
    run_id: str,
    flow_key: str,
    handoff_envelope: Optional[HandoffEnvelope] = None,
    receipt_reader: Optional[ReceiptReader] = None,
) -> Tuple[Optional[str], str]:
    """Determine the next step based on routing config and result.

    Supports three routing patterns:
    - linear: Simple sequential flow to the next step
    - microloop: Loops back to a target step until a condition is met
    - branch: Chooses next step based on result values

    When a HandoffEnvelope is provided, uses its RoutingSignal for routing
    decisions. Otherwise, falls back to receipt-based routing.

    Args:
        flow_def: The flow definition with all steps.
        current_step: The step that just completed.
        result: The step execution result dictionary.
        loop_state: Dictionary tracking iteration counts per step.
        run_id: The run identifier (for reading receipts).
        flow_key: The flow key (for reading receipts).
        handoff_envelope: Optional HandoffEnvelope with routing signal.
        receipt_reader: Optional function to read receipt fields.

    Returns:
        Tuple of (next_step_id or None if flow is complete, reason string).
    """
    routing = current_step.routing

    # Use handoff envelope if available
    if handoff_envelope is not None:
        signal = handoff_envelope.routing_signal
        if signal.decision == RoutingDecision.TERMINATE:
            return None, signal.reason or "flow_complete_via_signal"
        elif signal.decision == RoutingDecision.ADVANCE:
            next_step_id = signal.next_step_id
            if next_step_id is None and routing and routing.next:
                next_step_id = routing.next
            return next_step_id, signal.reason or "advance_via_signal"
        elif signal.decision == RoutingDecision.LOOP:
            if routing and routing.loop_target:
                loop_key = f"{current_step.id}:{routing.loop_target}"
                current_iter = loop_state.get(loop_key, 0)
                loop_state[loop_key] = current_iter + 1
                return routing.loop_target, signal.reason or f"loop_iteration:{current_iter + 1}"
        elif signal.decision == RoutingDecision.BRANCH:
            next_step_id = signal.next_step_id
            if next_step_id:
                return next_step_id, signal.reason or "branch_via_signal"

        # Signal didn't resolve, fall through
        logger.debug(
            "RoutingSignal did not resolve routing for step %s (decision=%s), falling back",
            current_step.id,
            signal.decision,
        )

    # Fallback: receipt-based routing
    if routing is None:
        # Default linear behavior: find next step by index
        next_step = None
        for step in flow_def.steps:
            if step.index == current_step.index + 1:
                next_step = step
                break
        if next_step:
            return next_step.id, "linear_default"
        return None, "flow_complete_no_routing"

    # Handle routing based on kind
    if routing.kind == "linear":
        if routing.next:
            return routing.next, "linear_explicit"
        return None, "flow_complete_linear"

    elif routing.kind == "microloop":
        return _route_microloop(
            current_step, routing, loop_state, run_id, flow_key, receipt_reader
        )

    elif routing.kind == "branch":
        # Branch routing based on result values
        if routing.branches and result.get("status"):
            branch_key = result.get("status")
            if branch_key in routing.branches:
                return routing.branches[branch_key], f"branch:{branch_key}"

        # Fallback to next
        if routing.next:
            return routing.next, "branch_fallback"
        return None, "flow_complete_branch"

    # Unknown routing kind, fall back to linear
    logger.warning("Unknown routing kind '%s', falling back to linear", routing.kind)
    if routing.next:
        return routing.next, "unknown_kind_fallback"
    return None, "flow_complete_unknown"


def _route_microloop(
    current_step: StepDefinition,
    routing: Any,  # StepRouting
    loop_state: Dict[str, int],
    run_id: str,
    flow_key: str,
    receipt_reader: Optional[ReceiptReader] = None,
) -> Tuple[Optional[str], str]:
    """Handle microloop routing.

    Args:
        current_step: The step that just completed.
        routing: The step's routing configuration.
        loop_state: Dictionary tracking iteration counts.
        run_id: The run identifier.
        flow_key: The flow key.
        receipt_reader: Optional function to read receipt fields.

    Returns:
        Tuple of (next_step_id or None, reason string).
    """
    loop_key = f"{current_step.id}:{routing.loop_target}"
    current_iter = loop_state.get(loop_key, 0)

    # Safety check: max iterations
    if current_iter >= routing.max_iterations:
        logger.warning(
            "Microloop %s reached max iterations (%d), exiting to next step",
            loop_key,
            routing.max_iterations,
        )
        if routing.next:
            return routing.next, f"max_iterations_reached:{routing.max_iterations}"
        return None, f"flow_complete_max_iterations:{routing.max_iterations}"

    # Check loop condition from receipt
    if routing.loop_condition_field and receipt_reader:
        agent_key = current_step.agents[0] if current_step.agents else "unknown"
        field_value = receipt_reader(
            run_id, flow_key, current_step.id, agent_key, routing.loop_condition_field
        )

        if field_value and field_value in routing.loop_success_values:
            # Condition met, exit loop
            if routing.next:
                return routing.next, f"loop_exit_condition_met:{field_value}"
            return None, f"flow_complete_condition_met:{field_value}"

        # Check can_further_iteration_help field as fallback
        can_iterate = receipt_reader(
            run_id, flow_key, current_step.id, agent_key, "can_further_iteration_help"
        )
        if can_iterate and can_iterate.lower() == "no":
            # Critic says no further iteration will help
            if routing.next:
                return routing.next, "loop_exit_no_further_help"
            return None, "flow_complete_no_further_help"

    # Loop back to target
    if routing.loop_target:
        loop_state[loop_key] = current_iter + 1
        return routing.loop_target, f"loop_iteration:{current_iter + 1}"

    # Fallback to next if no loop target
    if routing.next:
        return routing.next, "microloop_no_target"
    return None, "flow_complete_microloop_fallback"


def build_routing_context(
    current_step: StepDefinition,
    loop_state: Dict[str, int],
) -> "RoutingContext":
    """Build a RoutingContext for inclusion in step execution context.

    Args:
        current_step: The step being executed.
        loop_state: Dictionary tracking iteration counts.

    Returns:
        RoutingContext with loop state information.
    """
    from swarm.runtime.engines.models import RoutingContext

    routing = current_step.routing

    if routing is None:
        return RoutingContext(
            loop_iteration=0,
            max_iterations=None,
            decision="advance",
            reason="no_routing_config",
        )

    if routing.kind != "microloop":
        return RoutingContext(
            loop_iteration=0,
            max_iterations=None,
            decision="advance",
            reason=f"routing_kind:{routing.kind}",
        )

    loop_key = f"{current_step.id}:{routing.loop_target}"
    current_iter = loop_state.get(loop_key, 0)

    return RoutingContext(
        loop_iteration=current_iter,
        max_iterations=routing.max_iterations,
        decision="pending",
        reason="",
    )


__all__ = [
    "create_routing_signal",
    "route_step",
    "build_routing_context",
    "ReceiptReader",
]
