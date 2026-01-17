"""Path helpers for pack configuration files."""

from __future__ import annotations

from pathlib import Path


def get_baseline_pack_path() -> Path:
    """Get path to the baseline pack bundled with the runtime."""
    return Path(__file__).resolve().parents[2] / "packs" / "baseline" / "pack.yaml"


def get_repo_pack_path(repo_root: Path) -> Path:
    """Get path to the repo pack."""
    return repo_root / ".swarm" / "pack.yaml"


def get_pack_lock_path(repo_root: Path) -> Path:
    """Get path to the pack lock file."""
    return repo_root / ".swarm" / "pack.lock.json"
