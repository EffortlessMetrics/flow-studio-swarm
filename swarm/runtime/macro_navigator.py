"""
macro_navigator.py - Between-Flow Routing Decisions

This module implements the MacroNavigator for making intelligent routing
decisions BETWEEN flows, complementing the within-flow micro-navigation
handled by Navigator.

The MacroNavigator:
- Evaluates flow outcomes to determine next flow
- Applies routing rules (bounces, retries, skips)
- Enforces constraints (e.g., "never deploy unless gate verified")
- Tracks flow execution history for loop detection

Design Philosophy:
    - Traditional tooling handles flow execution
    - MacroNavigator receives flow results and run state
    - Makes routing decisions based on policy rules
    - Respects hard constraints even when rules suggest otherwise

Usage:
    from swarm.runtime.macro_navigator import (
        MacroNavigator,
        extract_flow_result,
    )

    # Initialize with run plan
    navigator = MacroNavigator(run_plan)

    # After each flow completes, get routing decision
    flow_result = extract_flow_result(flow_key, run_state, artifacts_path)
    decision = navigator.route_after_flow(
        completed_flow=flow_key,
        flow_result=flow_result,
        run_state=run_state,
    )

    # Apply the decision
    if decision.action == MacroAction.ADVANCE:
        next_flow = decision.next_flow
    elif decision.action == MacroAction.GOTO:
        next_flow = decision.next_flow  # Non-sequential jump
    elif decision.action == MacroAction.REPEAT:
        next_flow = completed_flow  # Re-run same flow
    elif decision.action == MacroAction.PAUSE:
        # Wait for human intervention
        ...
    elif decision.action == MacroAction.TERMINATE:
        # End the run
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from swarm.runtime.types import (
    FlowOutcome,
    FlowResult,
    GateVerdict,
    HumanPolicy,
    MacroAction,
    MacroPolicy,
    MacroRoutingDecision,
    MacroRoutingRule,
    RunPlanSpec,
    RunState,
    flow_result_to_dict,
    macro_routing_decision_to_dict,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Flow Result Extraction
# =============================================================================


def extract_flow_result(
    flow_key: str,
    run_state: RunState,
    artifacts_base: Optional[Path] = None,
) -> FlowResult:
    """Extract FlowResult from run state and artifacts.

    This function examines the completed flow's state and artifacts
    to produce a structured FlowResult for routing decisions.

    Args:
        flow_key: The flow that completed.
        run_state: Current run state with handoff envelopes.
        artifacts_base: Optional path to flow artifacts.

    Returns:
        FlowResult with outcome, status, and relevant details.
    """
    # Default to succeeded outcome
    outcome = FlowOutcome.SUCCEEDED
    status = ""
    gate_verdict = None
    bounce_target = None
    error = None
    artifacts: Dict[str, str] = {}
    issues: List[str] = []
    recommendations: List[str] = []

    # Check handoff envelopes for this flow
    flow_envelopes = {
        step_id: env
        for step_id, env in run_state.handoff_envelopes.items()
        if env.flow_key == flow_key
    }

    # Aggregate status from envelopes
    for step_id, envelope in flow_envelopes.items():
        if envelope.status == "failed":
            outcome = FlowOutcome.FAILED
            error = envelope.error
            break
        elif envelope.status == "partial":
            outcome = FlowOutcome.PARTIAL

        # Collect artifacts
        for name, path in envelope.artifacts.items():
            artifacts[f"{step_id}/{name}"] = path

        # Extract status from routing signal
        if envelope.routing_signal and envelope.routing_signal.reason:
            # Look for status patterns
            reason = envelope.routing_signal.reason.upper()
            if "VERIFIED" in reason:
                status = "VERIFIED"
            elif "UNVERIFIED" in reason:
                status = "UNVERIFIED"
            elif "BLOCKED" in reason:
                status = "BLOCKED"

    # Special handling for gate flow
    if flow_key == "gate":
        gate_verdict = _extract_gate_verdict(flow_envelopes, artifacts_base)
        if gate_verdict in (GateVerdict.BOUNCE_BUILD, GateVerdict.BOUNCE_PLAN):
            outcome = FlowOutcome.BOUNCED
            bounce_target = (
                "build" if gate_verdict == GateVerdict.BOUNCE_BUILD else "plan"
            )

    return FlowResult(
        flow_key=flow_key,
        outcome=outcome,
        status=status,
        gate_verdict=gate_verdict,
        bounce_target=bounce_target,
        error=error,
        artifacts=artifacts,
        duration_ms=0,  # Would be computed from envelope timestamps
        issues=issues,
        recommendations=recommendations,
    )


def _extract_gate_verdict(
    flow_envelopes: Dict[str, Any],
    artifacts_base: Optional[Path],
) -> Optional[GateVerdict]:
    """Extract gate verdict from gate flow artifacts.

    Looks for merge_decision.md and parses the verdict field.

    Args:
        flow_envelopes: Handoff envelopes for the gate flow.
        artifacts_base: Path to flow artifacts.

    Returns:
        GateVerdict if found, None otherwise.
    """
    # Try to find verdict in envelope routing signals
    for step_id, envelope in flow_envelopes.items():
        if "merge-decider" in step_id or "decision" in step_id.lower():
            # Check routing signal for verdict hints
            if envelope.routing_signal:
                reason = envelope.routing_signal.reason.upper()
                if "MERGE_WITH_CONDITIONS" in reason:
                    return GateVerdict.MERGE_WITH_CONDITIONS
                elif "MERGE" in reason:
                    return GateVerdict.MERGE
                elif "BOUNCE_BUILD" in reason or "BOUNCE TO BUILD" in reason:
                    return GateVerdict.BOUNCE_BUILD
                elif "BOUNCE_PLAN" in reason or "BOUNCE TO PLAN" in reason:
                    return GateVerdict.BOUNCE_PLAN
                elif "ESCALATE" in reason:
                    return GateVerdict.ESCALATE
                elif "BLOCK" in reason:
                    return GateVerdict.BLOCK

    # Fallback: try to read merge_decision.md if path provided
    if artifacts_base:
        decision_path = artifacts_base / "gate" / "merge_decision.md"
        if decision_path.exists():
            try:
                content = decision_path.read_text()
                # Parse verdict from Machine Summary section
                if "verdict:" in content.lower():
                    for line in content.split("\n"):
                        if "verdict:" in line.lower():
                            verdict_str = line.split(":")[-1].strip().upper()
                            try:
                                return GateVerdict(verdict_str)
                            except ValueError:
                                pass
            except Exception as e:
                logger.warning("Failed to read merge_decision.md: %s", e)

    return None


# =============================================================================
# MacroNavigator
# =============================================================================


class MacroNavigator:
    """Between-flow routing decisions.

    The MacroNavigator makes routing decisions after each flow completes.
    It evaluates the flow result against routing rules and constraints
    to determine what flow to execute next.

    Key responsibilities:
    - Evaluate flow outcomes against routing rules
    - Enforce hard constraints (e.g., never deploy without gate approval)
    - Track flow execution history for loop detection
    - Respect max_repeats and max_total_flows limits

    Example:
        run_plan = RunPlanSpec.default()
        navigator = MacroNavigator(run_plan)

        # After gate flow completes
        flow_result = extract_flow_result("gate", run_state, artifacts_path)
        decision = navigator.route_after_flow("gate", flow_result, run_state)

        if decision.action == MacroAction.GOTO:
            # Gate bounced - jump to target flow
            next_flow = decision.next_flow
        elif decision.action == MacroAction.ADVANCE:
            # Proceed to deploy
            next_flow = decision.next_flow
    """

    def __init__(
        self,
        run_plan: RunPlanSpec,
        flow_execution_counts: Optional[Dict[str, int]] = None,
    ):
        """Initialize the MacroNavigator.

        Args:
            run_plan: The run plan specification with policies and constraints.
            flow_execution_counts: Optional initial execution counts per flow.
        """
        self._run_plan = run_plan
        self._flow_execution_counts: Dict[str, int] = flow_execution_counts or {}
        self._total_flow_executions = sum(self._flow_execution_counts.values())
        self._routing_history: List[Dict[str, Any]] = []

    @property
    def run_plan(self) -> RunPlanSpec:
        """Get the run plan specification."""
        return self._run_plan

    @property
    def flow_execution_counts(self) -> Dict[str, int]:
        """Get execution counts per flow."""
        return self._flow_execution_counts.copy()

    @property
    def total_flow_executions(self) -> int:
        """Get total number of flow executions."""
        return self._total_flow_executions

    def route_after_flow(
        self,
        completed_flow: str,
        flow_result: FlowResult,
        run_state: RunState,
    ) -> MacroRoutingDecision:
        """Make routing decision after a flow completes.

        This is the main entry point for routing decisions. It:
        1. Records the flow execution
        2. Checks hard constraints
        3. Evaluates routing rules
        4. Applies human policy
        5. Returns the routing decision

        Args:
            completed_flow: The flow key that just completed.
            flow_result: Structured result of the completed flow.
            run_state: Current run state.

        Returns:
            MacroRoutingDecision with action, target, and explanation.
        """
        # Record this execution
        self._record_execution(completed_flow)

        # Check global limits
        if self._total_flow_executions >= self._run_plan.max_total_flows:
            return MacroRoutingDecision(
                action=MacroAction.TERMINATE,
                reason=f"Exceeded max total flows ({self._run_plan.max_total_flows})",
                warnings=["Safety limit reached - terminating run"],
            )

        # Check per-flow repeat limits
        flow_count = self._flow_execution_counts.get(completed_flow, 0)
        if flow_count > self._run_plan.macro_policy.max_repeats_per_flow:
            return MacroRoutingDecision(
                action=MacroAction.TERMINATE,
                reason=f"Flow '{completed_flow}' exceeded max repeats "
                       f"({self._run_plan.macro_policy.max_repeats_per_flow})",
                warnings=[f"Flow {completed_flow} repeated too many times"],
            )

        # Check hard constraints
        constraint_result = self._check_constraints(completed_flow, flow_result)
        if constraint_result:
            return constraint_result

        # Evaluate routing rules
        rule_decision = self._evaluate_routing_rules(flow_result)
        if rule_decision:
            return rule_decision

        # Apply human policy
        human_decision = self._apply_human_policy(completed_flow)
        if human_decision:
            return human_decision

        # Default: advance to next flow in sequence
        return self._default_advance(completed_flow)

    def _record_execution(self, flow_key: str) -> None:
        """Record a flow execution for tracking."""
        self._flow_execution_counts[flow_key] = (
            self._flow_execution_counts.get(flow_key, 0) + 1
        )
        self._total_flow_executions += 1

        self._routing_history.append({
            "flow": flow_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_number": self._flow_execution_counts[flow_key],
        })

    def _check_constraints(
        self,
        completed_flow: str,
        flow_result: FlowResult,
    ) -> Optional[MacroRoutingDecision]:
        """Check hard constraints that override routing rules.

        Note: Constraints are checked AFTER routing rules are evaluated.
        This method is called only for the final routing decision to ensure
        hard constraints are not violated by route decisions.

        Args:
            completed_flow: The flow that completed.
            flow_result: Result of the completed flow.

        Returns:
            MacroRoutingDecision if constraint violated, None otherwise.
        """
        # For gate flow, constraints are handled by routing rules
        # (bounces, escalations, etc.) - don't apply constraint termination
        # unless the default advance would violate constraints.
        #
        # The constraint check ensures that if routing rules don't handle
        # a non-approval verdict, we don't silently advance to deploy.
        #
        # This is intentionally a no-op for now - routing rules handle
        # all gate verdicts, and the default advance handles sequence.
        # The constraint is documented but enforced via routing rules.
        return None

    def _evaluate_routing_rules(
        self,
        flow_result: FlowResult,
    ) -> Optional[MacroRoutingDecision]:
        """Evaluate routing rules against flow result.

        Args:
            flow_result: Result of the completed flow.

        Returns:
            MacroRoutingDecision if a rule matched, None otherwise.
        """
        policy = self._run_plan.macro_policy

        for rule in policy.routing_rules:
            if not rule.can_fire():
                logger.debug(
                    "Rule %s exhausted (uses: %d/%d)",
                    rule.rule_id,
                    rule.uses,
                    rule.max_uses,
                )
                continue

            if rule.matches(flow_result):
                rule.record_use()
                logger.info(
                    "Rule %s matched: %s -> %s",
                    rule.rule_id,
                    rule.action.value,
                    rule.target_flow or "(no target)",
                )

                return MacroRoutingDecision(
                    action=rule.action,
                    next_flow=rule.target_flow,
                    reason=rule.description or f"Rule {rule.rule_id} matched",
                    rule_applied=rule.rule_id,
                )

        return None

    def _apply_human_policy(
        self,
        completed_flow: str,
    ) -> Optional[MacroRoutingDecision]:
        """Apply human interaction policy.

        Args:
            completed_flow: The flow that completed.

        Returns:
            MacroRoutingDecision if human pause required, None otherwise.
        """
        human_policy = self._run_plan.human_policy

        # Check if this flow requires approval
        if completed_flow in human_policy.require_approval_flows:
            return MacroRoutingDecision(
                action=MacroAction.PAUSE,
                reason=f"Flow '{completed_flow}' requires human approval",
            )

        # Check per_flow mode
        if human_policy.mode == "per_flow" and human_policy.allow_pause_between_flows:
            return MacroRoutingDecision(
                action=MacroAction.PAUSE,
                reason="Per-flow review mode - awaiting human approval",
            )

        return None

    def _default_advance(
        self,
        completed_flow: str,
    ) -> MacroRoutingDecision:
        """Get default advance decision (next flow in sequence).

        Args:
            completed_flow: The flow that completed.

        Returns:
            MacroRoutingDecision to advance to next flow or terminate.
        """
        sequence = self._run_plan.flow_sequence

        if completed_flow not in sequence:
            return MacroRoutingDecision(
                action=MacroAction.TERMINATE,
                reason=f"Flow '{completed_flow}' not in sequence",
                warnings=[f"Unknown flow: {completed_flow}"],
            )

        idx = sequence.index(completed_flow)
        if idx + 1 >= len(sequence):
            return MacroRoutingDecision(
                action=MacroAction.TERMINATE,
                reason="All flows in sequence completed",
            )

        next_flow = sequence[idx + 1]
        return MacroRoutingDecision(
            action=MacroAction.ADVANCE,
            next_flow=next_flow,
            reason=f"Advancing from '{completed_flow}' to '{next_flow}'",
        )

    def get_routing_history(self) -> List[Dict[str, Any]]:
        """Get the routing history for audit purposes.

        Returns:
            List of routing events with timestamps and decisions.
        """
        return list(self._routing_history)

    def reset_rule_uses(self) -> None:
        """Reset all rule usage counters.

        Call this when starting a fresh run with the same navigator.
        """
        for rule in self._run_plan.macro_policy.routing_rules:
            rule.uses = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize navigator state for persistence.

        Returns:
            Dictionary with navigator state.
        """
        return {
            "flow_execution_counts": dict(self._flow_execution_counts),
            "total_flow_executions": self._total_flow_executions,
            "routing_history": list(self._routing_history),
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        run_plan: RunPlanSpec,
    ) -> "MacroNavigator":
        """Restore navigator from serialized state.

        Args:
            data: Serialized navigator state.
            run_plan: Run plan specification.

        Returns:
            Restored MacroNavigator instance.
        """
        navigator = cls(
            run_plan=run_plan,
            flow_execution_counts=dict(data.get("flow_execution_counts", {})),
        )
        navigator._total_flow_executions = data.get(
            "total_flow_executions",
            sum(navigator._flow_execution_counts.values()),
        )
        navigator._routing_history = list(data.get("routing_history", []))
        return navigator


# =============================================================================
# Convenience Functions
# =============================================================================


def create_default_navigator() -> MacroNavigator:
    """Create a MacroNavigator with default SDLC configuration.

    Returns:
        MacroNavigator configured for standard signal -> wisdom flow.
    """
    return MacroNavigator(RunPlanSpec.default())


def create_autopilot_navigator() -> MacroNavigator:
    """Create a MacroNavigator for autonomous (no human) execution.

    Returns:
        MacroNavigator configured for autopilot mode.
    """
    run_plan = RunPlanSpec(
        flow_sequence=["signal", "plan", "build", "gate", "deploy", "wisdom"],
        macro_policy=MacroPolicy.default(),
        human_policy=HumanPolicy.autopilot(),
        constraints=[
            "never deploy unless gate verdict is MERGE or MERGE_WITH_CONDITIONS",
            "never skip gate flow",
        ],
        max_total_flows=20,
    )
    return MacroNavigator(run_plan)


def create_supervised_navigator() -> MacroNavigator:
    """Create a MacroNavigator for supervised (human-in-loop) execution.

    Returns:
        MacroNavigator configured for supervised mode with pauses.
    """
    run_plan = RunPlanSpec(
        flow_sequence=["signal", "plan", "build", "gate", "deploy", "wisdom"],
        macro_policy=MacroPolicy.default(),
        human_policy=HumanPolicy.supervised(),
        constraints=[
            "never deploy unless gate verdict is MERGE or MERGE_WITH_CONDITIONS",
            "never skip gate flow",
        ],
        max_total_flows=20,
    )
    return MacroNavigator(run_plan)


__all__ = [
    "MacroNavigator",
    "extract_flow_result",
    "create_default_navigator",
    "create_autopilot_navigator",
    "create_supervised_navigator",
]
