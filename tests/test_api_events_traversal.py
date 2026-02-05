from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from swarm.api.routes.events import stream_run_events


@pytest.mark.anyio
async def test_stream_run_events_traversal_direct(tmp_path):
    """
    Test that path traversal in run_id is blocked for the events endpoint logic.
    """
    # Setup directory structure
    repo_root = tmp_path
    swarm_dir = repo_root / "swarm"
    runs_dir = swarm_dir / "runs"

    runs_dir.mkdir(parents=True)

    # Mock Request
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    # Mock get_spec_manager
    mock_manager = MagicMock()
    mock_manager.runs_root = runs_dir

    with patch("swarm.api.server.get_spec_manager", return_value=mock_manager):
        with patch("swarm.runtime.resilient_db.check_db_health"):

            # Try traversal
            traversal_run_id = "../secret"

            # Expect HTTPException (400)
            with pytest.raises(HTTPException) as excinfo:
                await stream_run_events(traversal_run_id, mock_request)

            assert excinfo.value.status_code == 400
            assert (
                "traversal sequence" in str(excinfo.value.detail)
                or "invalid characters" in str(excinfo.value.detail)
                or "invalid_run_id" in str(excinfo.value.detail)
            )

            print(f"Caught expected exception: {excinfo.value}")
