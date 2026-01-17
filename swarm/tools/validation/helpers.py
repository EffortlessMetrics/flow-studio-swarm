# swarm/tools/validation/helpers.py
"""Path resolution and utility functions for validation."""

from pathlib import Path
from typing import Any, Optional


def safe_get_stripped(value: Any) -> Optional[str]:
    """
    Safely extract and strip a value that might be None.

    Handles YAML null values (including tilde ~) gracefully.

    Args:
        value: Field value (could be None, string, etc.)

    Returns:
        Stripped string if value is a non-empty string, None otherwise
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped else None


def find_repo_root() -> Path:
    """Find repository root by looking for swarm/AGENTS.md."""
    current = Path.cwd().resolve()

    # Check current directory and parents
    for path in [current] + list(current.parents):
        agents_md = path / "swarm" / "AGENTS.md"
        if agents_md.is_file():
            return path

    # Fallback: assume we're in the repo root
    return current


# Resolved paths (initialized on import)
ROOT = find_repo_root()
AGENTS_MD = ROOT / "swarm" / "AGENTS.md"
FLOW_SPECS_DIR = ROOT / "swarm" / "flows"
FLOWS_CONFIG_DIR = ROOT / "swarm" / "config" / "flows"
AGENTS_DIR = ROOT / ".claude" / "agents"
SKILLS_DIR = ROOT / ".claude" / "skills"
