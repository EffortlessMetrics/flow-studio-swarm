import pytest
import json
import asyncio
from pathlib import Path
from swarm.api.services.run_state import RunStateManager

@pytest.mark.anyio
async def test_list_runs_async(tmp_path):
    """Verify list_runs_async returns runs correctly."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create a few runs
    created_runs = []
    for i in range(3):
        run_id = f"run-{i}"
        run_dir = runs_dir / run_id
        run_dir.mkdir()
        state = {
            "run_id": run_id,
            "status": "pending",
            "created_at": "2024-01-01T00:00:00Z"
        }
        (run_dir / "run_state.json").write_text(json.dumps(state))
        created_runs.append(run_id)

    manager = RunStateManager(runs_dir)

    # Call list_runs_async
    runs = await manager.list_runs_async()

    assert len(runs) == 3
    returned_ids = {r["run_id"] for r in runs}
    assert returned_ids == set(created_runs)
