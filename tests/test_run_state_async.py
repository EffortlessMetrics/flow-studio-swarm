import json
import threading
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from swarm.api.services.run_state import RunStateManager


@pytest.mark.anyio
async def test_list_runs_async_calls_list_runs_in_thread(tmp_path):
    """Test that list_runs_async calls list_runs via asyncio.to_thread."""
    manager = RunStateManager(tmp_path)

    # Mock list_runs to return a specific value and verify it was called
    expected_runs = [{"run_id": "test-run"}]

    main_thread = threading.current_thread()
    executed_in_thread = None

    def mock_list_runs(limit=20):
        nonlocal executed_in_thread
        executed_in_thread = threading.current_thread()
        return expected_runs

    with patch.object(manager, "list_runs", side_effect=mock_list_runs) as mock_method:
        result = await manager.list_runs_async(limit=10)

        assert result == expected_runs
        mock_method.assert_called_once_with(limit=10)

        # Verify it ran in a different thread
        assert executed_in_thread is not None
        assert executed_in_thread != main_thread


@pytest.mark.anyio
async def test_list_runs_async_integration(tmp_path):
    """Integration test for list_runs_async with real file I/O."""
    manager = RunStateManager(tmp_path)

    # Create a dummy run state
    run_id = "run-async-test"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    state = {
        "run_id": run_id,
        "flow_id": "flow-test",
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    (run_dir / "run_state.json").write_text(json.dumps(state), encoding="utf-8")

    # Call async method
    runs = await manager.list_runs_async(limit=10)

    assert len(runs) == 1
    assert runs[0]["run_id"] == run_id
    assert runs[0]["status"] == "completed"
