"""
Shared helpers for RunStateManager tests.

One importable home for the fixtures used by the run state suites
(test_run_state_crud.py, test_run_state_storage.py). `tests/` is placed on
sys.path by conftest.py, so these import as a flat module.
"""

import json
from pathlib import Path

from swarm.api.services.run_state import RunStateManager


def make_manager(tmp_path: Path) -> RunStateManager:
    """Build a manager rooted at a temporary runs directory."""
    runs_root = tmp_path / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    return RunStateManager(runs_root=runs_root)


def write_run(runs_root: Path, run_id: str, **overrides) -> None:
    """Write a run_state.json directly to disk, bypassing the manager."""
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": run_id,
        "flow_id": "3-build",
        "status": "pending",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    state.update(overrides)
    (run_dir / "run_state.json").write_text(json.dumps(state), encoding="utf-8")
