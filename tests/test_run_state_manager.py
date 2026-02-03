import pytest
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from swarm.api.services.run_state import RunStateManager

@pytest.fixture
def run_state_manager(tmp_path):
    return RunStateManager(tmp_path)

@pytest.mark.anyio
async def test_list_runs_async_returns_correct_data(run_state_manager):
    """Test that list_runs_async returns correct data."""
    # Create test runs
    runs_dir = run_state_manager.runs_root

    # Run 1
    run1_id = "run-1"
    (runs_dir / run1_id).mkdir()
    state1 = {
        "run_id": run1_id,
        "flow_id": "flow-1",
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (runs_dir / run1_id / "run_state.json").write_text(json.dumps(state1))

    # Run 2
    run2_id = "run-2"
    (runs_dir / run2_id).mkdir()
    state2 = {
        "run_id": run2_id,
        "flow_id": "flow-2",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (runs_dir / run2_id / "run_state.json").write_text(json.dumps(state2))

    # Run async list
    runs = await run_state_manager.list_runs_async()

    assert len(runs) == 2
    run_ids = {r["run_id"] for r in runs}
    assert "run-1" in run_ids
    assert "run-2" in run_ids

@pytest.mark.anyio
async def test_list_runs_async_matches_sync(run_state_manager):
    """Test that list_runs_async matches sync list_runs output."""
    runs_dir = run_state_manager.runs_root

    for i in range(5):
        run_id = f"run-{i}"
        (runs_dir / run_id).mkdir()
        state = {
            "run_id": run_id,
            "flow_id": f"flow-{i}",
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (runs_dir / run_id / "run_state.json").write_text(json.dumps(state))

    sync_runs = run_state_manager.list_runs()
    async_runs = await run_state_manager.list_runs_async()

    assert sync_runs == async_runs

@pytest.mark.anyio
async def test_list_runs_async_handles_empty(run_state_manager):
    runs = await run_state_manager.list_runs_async()
    assert runs == []

@pytest.mark.anyio
async def test_list_runs_async_respects_limit(run_state_manager):
    runs_dir = run_state_manager.runs_root

    for i in range(10):
        run_id = f"run-{i}"
        (runs_dir / run_id).mkdir()
        state = {
            "run_id": run_id,
            "flow_id": f"flow-{i}",
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (runs_dir / run_id / "run_state.json").write_text(json.dumps(state))

    runs = await run_state_manager.list_runs_async(limit=3)
    assert len(runs) == 3
