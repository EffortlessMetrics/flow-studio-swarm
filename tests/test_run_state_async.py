import pytest
import asyncio
import json
from pathlib import Path
from swarm.api.services.run_state import RunStateManager

@pytest.mark.anyio
async def test_list_runs_async(tmp_path):
    """Test that list_runs_async returns runs correctly."""
    manager = RunStateManager(tmp_path)

    # Create dummy runs
    run1 = {
        "run_id": "run-1",
        "flow_id": "flow-a",
        "status": "completed",
        "created_at": "2024-01-01T00:00:00Z",
    }
    run2 = {
        "run_id": "run-2",
        "flow_id": "flow-b",
        "status": "pending",
        "created_at": "2024-01-02T00:00:00Z",
    }

    # Helper to write run state
    def create_run_state(run_data):
        run_dir = tmp_path / run_data["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        state_path = run_dir / "run_state.json"
        state_path.write_text(json.dumps(run_data))
        # Set mtime to ensure sorting order (run2 is newer)
        timestamp = 1704153600 if run_data["run_id"] == "run-1" else 1704240000
        import os
        os.utime(run_dir, (timestamp, timestamp))

    create_run_state(run1)
    create_run_state(run2)

    # Call list_runs_async
    runs = await manager.list_runs_async(limit=10)

    assert len(runs) == 2
    assert runs[0]["run_id"] == "run-2"
    assert runs[1]["run_id"] == "run-1"
