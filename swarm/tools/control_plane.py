#!/usr/bin/env python3
"""
Control plane layer for agent model configuration.

Enforces that:
1. Model values are from a known set (inherit, haiku, sonnet, opus)
2. Missing model defaults to 'inherit'
3. Model changes are logged for audit/visibility

Used by gen_adapters.py to validate and track model decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Known Claude model aliases
VALID_MODELS = {"inherit", "haiku", "sonnet", "opus"}


def _utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class ModelDecision:
    """Audit record for a model decision."""

    agent_key: str
    source: str  # "config", "override", "default"
    model: str
    previous_model: Optional[str] = None
    reason: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = _utc_now_iso()

    def as_line(self) -> str:
        """Format as audit log line."""
        change = ""
        if self.previous_model and self.previous_model != self.model:
            change = f" (changed from {self.previous_model})"
        reason_str = f" [{self.reason}]" if self.reason else ""
        return (
            f"{self.timestamp} {self.agent_key}: {self.source} -> {self.model}{change}{reason_str}"
        )


class ControlPlane:
    """
    Central authority for agent model configuration.

    Validates model choices, applies defaults, and maintains audit trail.
    """

    def __init__(self):
        self.decisions: list[ModelDecision] = []

    def resolve_model(
        self,
        agent_key: str,
        config_model: Optional[str],
        override_model: Optional[str],
    ) -> tuple[str, ModelDecision]:
        """
        Resolve the final model value for an agent.

        Args:
            agent_key: Agent identifier
            config_model: Model from agent config (may be None)
            override_model: Platform-specific override (may be None)

        Returns:
            (final_model, decision_record)

        Decision priority:
        1. Per-platform override (if explicitly set)
        2. Config value (if set)
        3. Default to "inherit"

        All values are validated against VALID_MODELS.
        """
        if override_model is not None:
            # Platform override is authoritative
            if override_model not in VALID_MODELS:
                raise ValueError(
                    f"Agent '{agent_key}': Invalid model '{override_model}' in "
                    f"platform override. Must be one of {VALID_MODELS}."
                )
            decision = ModelDecision(
                agent_key=agent_key,
                source="override",
                model=override_model,
                previous_model=config_model,
                reason="platform-specific override",
            )
        elif config_model is not None:
            # Config value is used
            if config_model not in VALID_MODELS:
                raise ValueError(
                    f"Agent '{agent_key}': Invalid model '{config_model}' in "
                    f"config. Must be one of {VALID_MODELS}."
                )
            decision = ModelDecision(
                agent_key=agent_key,
                source="config",
                model=config_model,
                reason="from agent config",
            )
        else:
            # Default to inherit
            decision = ModelDecision(
                agent_key=agent_key,
                source="default",
                model="inherit",
                reason="control plane default (model not specified in config)",
            )

        self.decisions.append(decision)
        return decision.model, decision

    def audit_log(self) -> str:
        """Generate human-readable audit log of all decisions."""
        if not self.decisions:
            return "# Control Plane Audit Log\n\nNo decisions recorded.\n"

        lines = ["# Control Plane Audit Log", ""]
        for decision in self.decisions:
            lines.append(decision.as_line())
        lines.append("")
        return "\n".join(lines)

    def write_audit_log(self, path: Path) -> None:
        """Write audit log to file."""
        path.write_text(self.audit_log(), encoding="utf-8")

    def changed_agents(self) -> Dict[str, tuple[str, str]]:
        """
        Return agents whose model was changed (config to override).

        Returns:
            {agent_key: (old_model, new_model)}
        """
        changes = {}
        for decision in self.decisions:
            if decision.source == "override" and decision.previous_model:
                if decision.previous_model != decision.model:
                    changes[decision.agent_key] = (
                        decision.previous_model,
                        decision.model,
                    )
        return changes

    def summary(self) -> Dict[str, Any]:
        """Return summary statistics of decisions."""
        by_source = {}
        by_model = {}

        for decision in self.decisions:
            # Count by source
            by_source[decision.source] = by_source.get(decision.source, 0) + 1
            # Count by model
            by_model[decision.model] = by_model.get(decision.model, 0) + 1

        return {
            "total_decisions": len(self.decisions),
            "by_source": by_source,
            "by_model": by_model,
            "changed_count": len(self.changed_agents()),
        }


def validate_model_value(model: str) -> None:
    """
    Validate a single model value.

    Raises ValueError if invalid.
    """
    if model not in VALID_MODELS:
        raise ValueError(f"Invalid model '{model}'. Must be one of {VALID_MODELS}.")
