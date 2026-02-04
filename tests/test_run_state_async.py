"""
Tests for asynchronous RunStateManager operations.
"""

import asyncio
import json
import pytest
from pathlib import Path
from swarm.api.services.run_state import RunStateManager
import os
import time


@pytest.mark.anyio
async def test_list_runs_async_success(tmp_path):
    """Test list_runs_async returns runs correctly."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    manager = RunStateManager(runs_dir)

    # Create dummy runs
    # We delay slightly to ensure mtime differences for sorting if needed,
    # though strict sorting isn't the primary thing being tested here, mostly the async execution.
    run_ids = ["run-a", "run-b", "run-c"]
    for run_id in run_ids:
        run_path = runs_dir / run_id
        run_path.mkdir()
        state = {
            "run_id": run_id,
            "status": "pending",
            "created_at": "2023-01-01T00:00:00Z",
        }
        (run_path / "run_state.json").write_text(json.dumps(state))
        time.sleep(0.01)  # Ensure distinct mtimes

    # Call list_runs_async
    # This assumes the method exists. If run before implementation, this test will error (AttributeError).
    runs = await manager.list_runs_async(limit=10)

    assert len(runs) == 3
    found_ids = [r["run_id"] for r in runs]
    for rid in run_ids:
        assert rid in found_ids


@pytest.mark.anyio
async def test_list_runs_async_empty(tmp_path):
    """Test list_runs_async with no runs."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    manager = RunStateManager(runs_dir)
    runs = await manager.list_runs_async()
    assert runs == []
