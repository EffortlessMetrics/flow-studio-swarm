import json
import os
import time
from datetime import datetime, timezone

from swarm.api.services.run_state import RunStateManager


def create_run_state(run_dir, run_id):
    state = {
        "run_id": run_id,
        "flow_id": "test-flow",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_state.json").write_text(json.dumps(state))
    return state

def test_run_state_manager_list_runs(tmp_path):
    """Test that list_runs correctly lists and sorts runs."""
    manager = RunStateManager(runs_root=tmp_path)

    # Create 5 runs with different timestamps
    for i in range(5):
        run_id = f"run-{i}"
        run_dir = tmp_path / run_id
        create_run_state(run_dir, run_id)

        # Set mtime: run-0 is oldest, run-4 is newest
        mtime = time.time() - (100 - i) * 10
        os.utime(run_dir, (mtime, mtime))

    # List runs with limit 3
    runs = manager.list_runs(limit=3)

    assert len(runs) == 3
    # Should be sorted new to old
    assert runs[0]["run_id"] == "run-4"
    assert runs[1]["run_id"] == "run-3"
    assert runs[2]["run_id"] == "run-2"

def test_run_state_manager_ignores_empty_dirs(tmp_path):
    """Test that list_runs ignores directories without run_state.json."""
    manager = RunStateManager(runs_root=tmp_path)

    # Create a valid run
    create_run_state(tmp_path / "valid-run", "valid-run")

    # Create an empty directory
    (tmp_path / "empty-dir").mkdir()

    # Create a directory with random file
    (tmp_path / "other-dir").mkdir()
    (tmp_path / "other-dir" / "readme.txt").touch()

    runs = manager.list_runs()

    assert len(runs) == 1
    assert runs[0]["run_id"] == "valid-run"

def test_run_state_manager_handles_corrupt_state(tmp_path):
    """Test that list_runs handles corrupt run_state.json."""
    manager = RunStateManager(runs_root=tmp_path)

    # Create a run with corrupt state
    run_dir = tmp_path / "corrupt-run"
    run_dir.mkdir()
    (run_dir / "run_state.json").write_text("{invalid_json")

    # Create a valid run
    create_run_state(tmp_path / "valid-run", "valid-run")

    runs = manager.list_runs()

    # Should only return the valid run
    assert len(runs) == 1
    assert runs[0]["run_id"] == "valid-run"
