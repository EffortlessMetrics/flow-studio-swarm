import pytest
import json
import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone
from swarm.api.services.run_state import RunStateManager

@pytest.mark.anyio
async def test_list_runs_async_success(tmp_path):
    """Test that list_runs_async returns correct runs."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    manager = RunStateManager(runs_dir)

    # Create test runs
    runs = [
        {"run_id": "run-1", "created_at": "2023-01-01T10:00:00+00:00", "status": "completed"},
        {"run_id": "run-2", "created_at": "2023-01-01T11:00:00+00:00", "status": "failed"},
    ]

    for run in runs:
        run_dir = runs_dir / run["run_id"]
        run_dir.mkdir()
        state_path = run_dir / "run_state.json"
        state_path.write_text(json.dumps(run))

        # Set mtime to match order (run-2 is newer)
        timestamp = datetime.fromisoformat(run["created_at"]).timestamp()
        os.utime(run_dir, (timestamp, timestamp))

    # Test list_runs_async
    result = await manager.list_runs_async(limit=10)

    assert len(result) == 2
    # Should be sorted by mtime descending (newest first)
    assert result[0]["run_id"] == "run-2"
    assert result[1]["run_id"] == "run-1"

@pytest.mark.anyio
async def test_list_runs_async_empty(tmp_path):
    """Test that list_runs_async handles empty directory."""
    runs_dir = tmp_path / "runs_empty"

    manager = RunStateManager(runs_dir)
    result = await manager.list_runs_async()
    assert result == []
