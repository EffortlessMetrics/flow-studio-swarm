
import asyncio
import json
import pytest
from pathlib import Path
from swarm.api.services.run_state import RunStateManager

@pytest.fixture
def run_state_manager(tmp_path):
    return RunStateManager(tmp_path)

def test_list_runs_async(run_state_manager, tmp_path):
    # Create some runs
    for i in range(5):
        run_id = f"run-{i}"
        run_dir = tmp_path / run_id
        run_dir.mkdir()
        state = {
            "run_id": run_id,
            "flow_id": "test-flow",
            "status": "completed",
            "created_at": "2023-01-01T00:00:00Z"
        }
        (run_dir / "run_state.json").write_text(json.dumps(state))

    async def _test():
        runs = await run_state_manager.list_runs_async(limit=10)
        assert len(runs) == 5
        # runs are sorted by mtime, which might be same for all, so check presence
        run_ids = [r["run_id"] for r in runs]
        for i in range(5):
            assert f"run-{i}" in run_ids

    asyncio.run(_test())

def test_list_runs_async_empty(run_state_manager):
    async def _test():
        runs = await run_state_manager.list_runs_async()
        assert len(runs) == 0

    asyncio.run(_test())
