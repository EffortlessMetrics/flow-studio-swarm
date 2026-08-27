"""
Shared fixtures and helpers for the RunStateManager test modules.

The RunStateManager suite is split by contract surface:

- test_run_state.py          - creation and retrieval
- test_run_state_updates.py  - updates, ETag concurrency, locking
- test_run_state_listing.py  - listing and durable writes

They share one importable home for setup so the split does not duplicate it.

Async methods are driven with asyncio.run(), matching the convention used by
tests/test_security_path_traversal.py (the suite does not depend on
pytest-asyncio).
"""

import json
from pathlib import Path

import pytest
from swarm.api.services.run_state import RunStateManager


@pytest.fixture
def manager(tmp_path):
    """A RunStateManager rooted at an empty temp directory."""
    return RunStateManager(runs_root=tmp_path / "runs")


def read_state_file(runs_root: Path, run_id: str) -> dict:
    """Read a run's persisted state straight off disk."""
    return json.loads((runs_root / run_id / "run_state.json").read_text(encoding="utf-8"))
