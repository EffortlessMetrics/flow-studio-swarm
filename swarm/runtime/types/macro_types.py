"""Macro navigation (between-flow routing) types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


def _get_default_flow_sequence() -> List[str]:
    """Get the default SDLC flow sequence from the registry."""
    try:
        from swarm.config.flow_registry import get_sdlc_flow_keys

        return get_sdlc_flow_keys()
    except ImportError:
        return ["signal", "plan", "build", "review", "gate", "deploy", "wisdom"]


class MacroAction(str, Enum):
    """Action to take between flows."""

    ADVANCE = "advance"
    REPEAT = "repeat"
    GOTO = "goto"
    SKIP = "skip"
    TERMINATE = "terminate"
    PAUSE = "pause"


class GateVerdict(str, Enum):
    """Gate (Flow 4) decision outcomes."""

    MERGE = "MERGE"
    MERGE_WITH_CONDITIONS = "MERGE_WITH_CONDITIONS"
    BOUNCE_BUILD = "BOUNCE_BUILD"
    BOUNCE_PLAN = "BOUNCE_PLAN"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class FlowOutcome(str, Enum):
    """Outcome status of a completed flow."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"
    BOUNCED = "bounced"
    SKIPPED = "skipped"


@dataclass
class FlowResult:
    """Result of a completed flow for macro-routing decisions."""

    flow_key: str
    outcome: FlowOutcome
    status: str = ""
    gate_verdict: Optional[GateVerdict] = None
    bounce_target: Optional[str] = None
    error: Optional[str] = None
    artifacts: Dict[str, str] = field(default_factory=dict)
    duration_ms: int = 0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class MacroRoutingRule:
    """A single routing rule for macro-navigation."""

    rule_id: str
    condition: str
    action: MacroAction
    target_flow: Optional[str] = None
    max_uses: int = 3
    uses: int = 0
    description: str = ""

    def matches(self, flow_result: "FlowResult") -> bool:
        """Evaluate if this rule matches the flow result."""
        ctx = {
            "flow": flow_result.flow_key,
            "outcome": flow_result.outcome.value,
            "status": flow_result.status,
            "gate.verdict": (flow_result.gate_verdict.value if flow_result.gate_verdict else None),
            "bounce_target": flow_result.bounce_target,
            "has_error": flow_result.error is not None,
        }

        try:
            condition = self.condition.strip()
            if " == " in condition:
                parts = condition.split(" == ")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip("'\"")
                    return str(ctx.get(key, "")) == value
            if " and " in condition.lower():
                sub_conditions = condition.lower().split(" and ")
                results = []
                for sub in sub_conditions:
                    sub = sub.strip()
                    if " == " in sub:
                        parts = sub.split(" == ")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().strip("'\"")
                            results.append(str(ctx.get(key, "")).lower() == value.lower())
                return all(results)
            return False
        except Exception:
            return False

    def can_fire(self) -> bool:
        """Check if this rule can still fire (hasn't exceeded max_uses)."""
        return self.uses < self.max_uses

    def record_use(self) -> None:
        """Record that this rule was used."""
        self.uses += 1

    def clone(self) -> "MacroRoutingRule":
        """Create a shallow copy."""
        return MacroRoutingRule(
            rule_id=self.rule_id,
            condition=self.condition,
            action=self.action,
            target_flow=self.target_flow,
            max_uses=self.max_uses,
            uses=self.uses,
            description=self.description,
        )


@dataclass
class MacroPolicy:
    """Policy for between-flow routing decisions."""

    allow_flow_repeat: bool = True
    max_repeats_per_flow: int = 3
    routing_rules: List[MacroRoutingRule] = field(default_factory=list)
    default_action: MacroAction = MacroAction.ADVANCE
    strict_gate: bool = True

    @classmethod
    def default(cls) -> "MacroPolicy":
        """Create a default macro policy with standard SDLC rules."""
        return cls(
            allow_flow_repeat=True,
            max_repeats_per_flow=3,
            routing_rules=[
                MacroRoutingRule(
                    rule_id="gate-bounce-build",
                    condition="gate.verdict == 'BOUNCE_BUILD'",
                    action=MacroAction.GOTO,
                    target_flow="build",
                    max_uses=2,
                    description="Gate bounced to build for fixable issues",
                ),
                MacroRoutingRule(
                    rule_id="gate-bounce-plan",
                    condition="gate.verdict == 'BOUNCE_PLAN'",
                    action=MacroAction.GOTO,
                    target_flow="plan",
                    max_uses=1,
                    description="Gate bounced to plan for design issues",
                ),
                MacroRoutingRule(
                    rule_id="gate-escalate",
                    condition="gate.verdict == 'ESCALATE'",
                    action=MacroAction.PAUSE,
                    description="Gate escalated to human for decision",
                ),
                MacroRoutingRule(
                    rule_id="gate-block",
                    condition="gate.verdict == 'BLOCK'",
                    action=MacroAction.TERMINATE,
                    description="Gate blocked - cannot proceed",
                ),
                MacroRoutingRule(
                    rule_id="flow-failed",
                    condition="outcome == 'failed'",
                    action=MacroAction.TERMINATE,
                    description="Flow failed with error",
                ),
            ],
            default_action=MacroAction.ADVANCE,
            strict_gate=True,
        )

    def clone(self) -> "MacroPolicy":
        """Create a deep-ish copy."""
        return MacroPolicy(
            allow_flow_repeat=self.allow_flow_repeat,
            max_repeats_per_flow=self.max_repeats_per_flow,
            routing_rules=[r.clone() for r in self.routing_rules],
            default_action=self.default_action,
            strict_gate=self.strict_gate,
        )


@dataclass
class HumanPolicy:
    """Policy for human interaction boundaries."""

    mode: str = "run_end"
    allow_pause_mid_flow: bool = False
    allow_pause_between_flows: bool = False
    end_boundary: str = "run_end"
    require_approval_flows: List[str] = field(default_factory=list)

    @classmethod
    def autopilot(cls) -> "HumanPolicy":
        """Autopilot mode: no human intervention until run end."""
        return cls(
            mode="run_end",
            allow_pause_mid_flow=False,
            allow_pause_between_flows=False,
            end_boundary="run_end",
            require_approval_flows=[],
        )

    @classmethod
    def supervised(cls) -> "HumanPolicy":
        """Supervised mode: pause after each flow for review."""
        return cls(
            mode="per_flow",
            allow_pause_mid_flow=False,
            allow_pause_between_flows=True,
            end_boundary="flow_end",
            require_approval_flows=["gate", "deploy"],
        )

    def clone(self) -> "HumanPolicy":
        """Create a copy."""
        return HumanPolicy(
            mode=self.mode,
            allow_pause_mid_flow=self.allow_pause_mid_flow,
            allow_pause_between_flows=self.allow_pause_between_flows,
            end_boundary=self.end_boundary,
            require_approval_flows=list(self.require_approval_flows),
        )


@dataclass
class RunPlanSpec:
    """Macro orchestration policy for flow chaining."""

    flow_sequence: List[str] = field(default_factory=_get_default_flow_sequence)
    macro_policy: MacroPolicy = field(default_factory=MacroPolicy.default)
    human_policy: HumanPolicy = field(default_factory=HumanPolicy.autopilot)
    constraints: List[str] = field(default_factory=list)
    max_total_flows: int = 20

    @classmethod
    def default(cls) -> "RunPlanSpec":
        """Create a default RunPlanSpec with standard SDLC configuration."""
        return cls(
            flow_sequence=_get_default_flow_sequence(),
            macro_policy=MacroPolicy.default(),
            human_policy=HumanPolicy.autopilot(),
            constraints=[
                "never deploy unless gate verdict is MERGE or MERGE_WITH_CONDITIONS",
                "never skip gate flow",
                "max 3 bounces between gate and build",
            ],
            max_total_flows=20,
        )

    def clone(self) -> "RunPlanSpec":
        """Create a deep copy significantly faster than copy.deepcopy."""
        return RunPlanSpec(
            flow_sequence=list(self.flow_sequence),
            macro_policy=self.macro_policy.clone(),
            human_policy=self.human_policy.clone(),
            constraints=list(self.constraints),
            max_total_flows=self.max_total_flows,
        )


@dataclass
class MacroRoutingDecision:
    """Decision from MacroNavigator about between-flow routing."""

    action: MacroAction
    next_flow: Optional[str] = None
    reason: str = ""
    rule_applied: Optional[str] = None
    confidence: float = 1.0
    constraints_checked: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def flow_result_to_dict(result: FlowResult) -> Dict[str, Any]:
    """Convert FlowResult to dictionary for serialization."""
    return {
        "flow_key": result.flow_key,
        "outcome": result.outcome.value,
        "status": result.status,
        "gate_verdict": result.gate_verdict.value if result.gate_verdict else None,
        "bounce_target": result.bounce_target,
        "error": result.error,
        "artifacts": dict(result.artifacts),
        "duration_ms": result.duration_ms,
        "issues": list(result.issues),
        "recommendations": list(result.recommendations),
    }


def flow_result_from_dict(data: Dict[str, Any]) -> FlowResult:
    """Parse FlowResult from dictionary."""
    gate_verdict = None
    if data.get("gate_verdict"):
        gate_verdict = GateVerdict(data["gate_verdict"])

    return FlowResult(
        flow_key=data.get("flow_key", ""),
        outcome=FlowOutcome(data.get("outcome", "succeeded")),
        status=data.get("status", ""),
        gate_verdict=gate_verdict,
        bounce_target=data.get("bounce_target"),
        error=data.get("error"),
        artifacts=dict(data.get("artifacts", {})),
        duration_ms=data.get("duration_ms", 0),
        issues=list(data.get("issues", [])),
        recommendations=list(data.get("recommendations", [])),
    )


def macro_routing_rule_to_dict(rule: MacroRoutingRule) -> Dict[str, Any]:
    """Convert MacroRoutingRule to dictionary."""
    return {
        "rule_id": rule.rule_id,
        "condition": rule.condition,
        "action": rule.action.value,
        "target_flow": rule.target_flow,
        "max_uses": rule.max_uses,
        "uses": rule.uses,
        "description": rule.description,
    }


def macro_routing_rule_from_dict(data: Dict[str, Any]) -> MacroRoutingRule:
    """Parse MacroRoutingRule from dictionary."""
    return MacroRoutingRule(
        rule_id=data.get("rule_id", ""),
        condition=data.get("condition", ""),
        action=MacroAction(data.get("action", "advance")),
        target_flow=data.get("target_flow"),
        max_uses=data.get("max_uses", 3),
        uses=data.get("uses", 0),
        description=data.get("description", ""),
    )


def macro_policy_to_dict(policy: MacroPolicy) -> Dict[str, Any]:
    """Convert MacroPolicy to dictionary."""
    return {
        "allow_flow_repeat": policy.allow_flow_repeat,
        "max_repeats_per_flow": policy.max_repeats_per_flow,
        "routing_rules": [macro_routing_rule_to_dict(r) for r in policy.routing_rules],
        "default_action": policy.default_action.value,
        "strict_gate": policy.strict_gate,
    }


def macro_policy_from_dict(data: Dict[str, Any]) -> MacroPolicy:
    """Parse MacroPolicy from dictionary."""
    return MacroPolicy(
        allow_flow_repeat=data.get("allow_flow_repeat", True),
        max_repeats_per_flow=data.get("max_repeats_per_flow", 3),
        routing_rules=[macro_routing_rule_from_dict(r) for r in data.get("routing_rules", [])],
        default_action=MacroAction(data.get("default_action", "advance")),
        strict_gate=data.get("strict_gate", True),
    )


def human_policy_to_dict(policy: HumanPolicy) -> Dict[str, Any]:
    """Convert HumanPolicy to dictionary."""
    return {
        "mode": policy.mode,
        "allow_pause_mid_flow": policy.allow_pause_mid_flow,
        "allow_pause_between_flows": policy.allow_pause_between_flows,
        "end_boundary": policy.end_boundary,
        "require_approval_flows": list(policy.require_approval_flows),
    }


def human_policy_from_dict(data: Dict[str, Any]) -> HumanPolicy:
    """Parse HumanPolicy from dictionary."""
    return HumanPolicy(
        mode=data.get("mode", "run_end"),
        allow_pause_mid_flow=data.get("allow_pause_mid_flow", False),
        allow_pause_between_flows=data.get("allow_pause_between_flows", False),
        end_boundary=data.get("end_boundary", "run_end"),
        require_approval_flows=list(data.get("require_approval_flows", [])),
    )


def run_plan_spec_to_dict(spec: RunPlanSpec) -> Dict[str, Any]:
    """Convert RunPlanSpec to dictionary."""
    return {
        "flow_sequence": list(spec.flow_sequence),
        "macro_policy": macro_policy_to_dict(spec.macro_policy),
        "human_policy": human_policy_to_dict(spec.human_policy),
        "constraints": list(spec.constraints),
        "max_total_flows": spec.max_total_flows,
    }


def run_plan_spec_from_dict(data: Dict[str, Any]) -> RunPlanSpec:
    """Parse RunPlanSpec from dictionary."""
    return RunPlanSpec(
        flow_sequence=list(data.get("flow_sequence", [])),
        macro_policy=macro_policy_from_dict(data.get("macro_policy", {})),
        human_policy=human_policy_from_dict(data.get("human_policy", {})),
        constraints=list(data.get("constraints", [])),
        max_total_flows=data.get("max_total_flows", 20),
    )


def macro_routing_decision_to_dict(decision: MacroRoutingDecision) -> Dict[str, Any]:
    """Convert MacroRoutingDecision to dictionary."""
    return {
        "action": decision.action.value,
        "next_flow": decision.next_flow,
        "reason": decision.reason,
        "rule_applied": decision.rule_applied,
        "confidence": decision.confidence,
        "constraints_checked": list(decision.constraints_checked),
        "warnings": list(decision.warnings),
    }


def macro_routing_decision_from_dict(data: Dict[str, Any]) -> MacroRoutingDecision:
    """Parse MacroRoutingDecision from dictionary."""
    return MacroRoutingDecision(
        action=MacroAction(data.get("action", "advance")),
        next_flow=data.get("next_flow"),
        reason=data.get("reason", ""),
        rule_applied=data.get("rule_applied"),
        confidence=data.get("confidence", 1.0),
        constraints_checked=list(data.get("constraints_checked", [])),
        warnings=list(data.get("warnings", [])),
    )
