import json
from datetime import datetime, timezone

import pytest
from swarm.api.services.run_state import RunStateManager


@pytest.mark.anyio
async def test_list_runs_async(tmp_path):
    """Verify list_runs_async returns expected runs without blocking."""
    # Setup
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    manager = RunStateManager(runs_dir)

    # Create dummy runs
    for i in range(3):
        run_id = f"run-{i}"
        run_dir = runs_dir / run_id
        run_dir.mkdir()

        state = {
            "run_id": run_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "flow_id": "test-flow"
        }

        (run_dir / "run_state.json").write_text(json.dumps(state))

    # We expect this method to be added to RunStateManager
    runs = await manager.list_runs_async(limit=10)

    assert len(runs) == 3
    # Check if run_ids are present
    found_ids = {r["run_id"] for r in runs}
    assert found_ids == {"run-0", "run-1", "run-2"}
