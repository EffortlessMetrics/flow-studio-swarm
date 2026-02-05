import json
from datetime import datetime, timezone

import pytest
from swarm.api.services.run_state import RunStateManager


@pytest.mark.anyio
async def test_list_runs_async_matches_sync(tmp_path):
    """Verify that list_runs_async returns the same results as list_runs."""
    # Setup
    manager = RunStateManager(runs_root=tmp_path)

    # Create some dummy runs
    for i in range(5):
        run_id = f"run-{i}"
        flow_id = f"flow-{i}"
        state = {
            "run_id": run_id,
            "flow_id": flow_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        run_dir = tmp_path / run_id
        run_dir.mkdir()
        (run_dir / "run_state.json").write_text(json.dumps(state))

    # Test sync
    sync_runs = manager.list_runs(limit=10)
    assert len(sync_runs) == 5

    # Test async
    async_runs = await manager.list_runs_async(limit=10)
    assert len(async_runs) == 5

    # Verify content matches
    assert sync_runs == async_runs


@pytest.mark.anyio
async def test_list_runs_async_limit(tmp_path):
    """Verify limit works in async version."""
    manager = RunStateManager(runs_root=tmp_path)

    for i in range(10):
        run_id = f"run-{i}"
        state = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        run_dir = tmp_path / run_id
        run_dir.mkdir()
        (run_dir / "run_state.json").write_text(json.dumps(state))

    async_runs = await manager.list_runs_async(limit=3)
    assert len(async_runs) == 3
