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


def set_repo_root(path: Path) -> None:
    """
    Set the repository root to a specific path.

    This updates all path constants in this module. Must be called before
    any validation modules are imported if you want to override the default
    repo root detection.

    Args:
        path: Path to repository root
    """
    global ROOT, AGENTS_MD, FLOW_SPECS_DIR, FLOWS_CONFIG_DIR, AGENTS_DIR, SKILLS_DIR
    ROOT = Path(path).resolve()
    AGENTS_MD = ROOT / "swarm" / "AGENTS.md"
    FLOW_SPECS_DIR = ROOT / "swarm" / "flows"
    FLOWS_CONFIG_DIR = ROOT / "swarm" / "config" / "flows"
    AGENTS_DIR = ROOT / ".claude" / "agents"
    SKILLS_DIR = ROOT / ".claude" / "skills"


# Resolved paths (initialized on import)
ROOT = find_repo_root()
AGENTS_MD = ROOT / "swarm" / "AGENTS.md"
FLOW_SPECS_DIR = ROOT / "swarm" / "flows"
FLOWS_CONFIG_DIR = ROOT / "swarm" / "config" / "flows"
AGENTS_DIR = ROOT / ".claude" / "agents"
SKILLS_DIR = ROOT / ".claude" / "skills"
