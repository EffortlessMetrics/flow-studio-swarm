import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from swarm.api.services.run_state import RunStateManager

def test_list_runs_async(tmp_path):
    """Test that list_runs_async works correctly and returns runs sorted by mtime."""
    manager = RunStateManager(tmp_path)

    # Create 5 runs with delays to ensure mtime differences
    run_ids = []
    for i in range(5):
        run_id = f"run-{i}"
        run_ids.append(run_id)
        run_dir = tmp_path / run_id
        run_dir.mkdir()

        state = {
            "run_id": run_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "flow_id": "test-flow"
        }
        (run_dir / "run_state.json").write_text(json.dumps(state))

        # Update mtime explicitly to ensure order (run-4 newest)
        # using a fake timestamp
        timestamp = 1000 + i * 10
        os.utime(run_dir, (timestamp, timestamp))

    async def run_test():
        # Limit to 3, expecting run-4, run-3, run-2
        runs = await manager.list_runs_async(limit=3)
        return runs

    runs = asyncio.run(run_test())

    assert len(runs) == 3
    assert runs[0]["run_id"] == "run-4"
    assert runs[1]["run_id"] == "run-3"
    assert runs[2]["run_id"] == "run-2"

def test_list_runs_async_empty(tmp_path):
    """Test list_runs_async with empty directory."""
    manager = RunStateManager(tmp_path)

    async def run_test():
        return await manager.list_runs_async(limit=10)

    runs = asyncio.run(run_test())
    assert runs == []

def test_list_runs_async_nonexistent(tmp_path):
    """Test list_runs_async with nonexistent directory."""
    nonexistent = tmp_path / "does-not-exist"
    manager = RunStateManager(nonexistent)

    async def run_test():
        return await manager.list_runs_async(limit=10)

    runs = asyncio.run(run_test())
    assert runs == []
