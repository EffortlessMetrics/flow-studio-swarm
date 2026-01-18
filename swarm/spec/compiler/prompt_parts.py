"""
Shared prompt primitives for spec compilation.

These helpers are separated from compiler_legacy so the new compiler package
can reuse them without importing legacy modules.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.spec.loader import load_fragments
from swarm.spec.types import StationSpec

# Claude preset content (default system prompt base)
CLAUDE_CODE_PRESET = """You are Claude, an AI assistant by Anthropic. You are helpful, harmless, and honest.
You have access to a set of tools to help accomplish tasks. Use them as needed."""

# System prompt presets
SYSTEM_PRESETS: Dict[str, str] = {
    "default": CLAUDE_CODE_PRESET,
    "claude_code": CLAUDE_CODE_PRESET,
    "minimal": "You are a helpful AI assistant.",
    "custom": "",  # Custom presets are loaded from identity.preset_content
}


def render_template(template: str, variables: Dict[str, Any]) -> str:
    """Render a Mustache-style template with {{variable}} substitution.

    Supports nested access like {{step.objective}} and {{run.base}}.
    """

    def get_nested(obj: Any, path: str) -> str:
        parts = path.split(".")
        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, "")
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return ""
        return str(current) if current else ""

    def replace_match(match: re.Match) -> str:
        var_path = match.group(1).strip()
        return get_nested(variables, var_path)

    return re.sub(r"\{\{([^}]+)\}\}", replace_match, template)


def build_system_append(
    station: StationSpec,
    scent_trail: Optional[str] = None,
) -> str:
    """Build the system prompt append from station identity."""
    parts: List[str] = []

    if station.identity.system_append:
        parts.append(station.identity.system_append.strip())

    if station.invariants:
        parts.append("\n## Invariants (Non-Negotiable)")
        for inv in station.invariants:
            parts.append(f"- {inv}")

    if scent_trail:
        trail = scent_trail[:1500]
        if len(scent_trail) > 1500:
            trail += "\n... (truncated)"
        parts.append("\n## Lessons from Previous Runs")
        parts.append(trail)

    return "\n".join(parts)


def build_system_append_v2(
    station: StationSpec,
    scent_trail: Optional[str] = None,
    repo_root: Optional[Path] = None,
    policy_invariants_ref: Optional[List[str]] = None,
) -> str:
    """Build the v2 system prompt append with policy fragment loading."""
    parts: List[str] = []

    if station.identity.system_append:
        parts.append(station.identity.system_append.strip())

    if policy_invariants_ref:
        fragment_content = load_fragments(
            policy_invariants_ref,
            repo_root,
            separator="\n\n",
        )
        if fragment_content:
            parts.append("\n## Policy Invariants (From Fragments)")
            parts.append(fragment_content)

    if station.invariants:
        parts.append("\n## Station Invariants (Non-Negotiable)")
        for inv in station.invariants:
            parts.append(f"- {inv}")

    if scent_trail:
        trail = scent_trail[:1500]
        if len(scent_trail) > 1500:
            trail += "\n... (truncated)"
        parts.append("\n## Lessons from Previous Runs")
        parts.append(trail)

    return "\n".join(parts)
