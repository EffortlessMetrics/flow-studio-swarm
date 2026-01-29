
import pytest
from pathlib import Path
from swarm.api.services.run_state import RunStateManager

@pytest.mark.anyio
async def test_list_runs_async(tmp_path):
    """Test that list_runs is async and returns correct results."""
    # Setup
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create some runs
    (runs_dir / "run-1").mkdir()
    (runs_dir / "run-1" / "run_state.json").write_text('{"run_id": "run-1", "status": "completed", "created_at": "2023-01-01T00:00:00Z"}')

    (runs_dir / "run-2").mkdir()
    (runs_dir / "run-2" / "run_state.json").write_text('{"run_id": "run-2", "status": "pending", "created_at": "2023-01-02T00:00:00Z"}')

    manager = RunStateManager(runs_dir)

    # Execute
    runs = await manager.list_runs()

    # Verify
    assert len(runs) == 2
    ids = [r["run_id"] for r in runs]
    assert "run-1" in ids
    assert "run-2" in ids
