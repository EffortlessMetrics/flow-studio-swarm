
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from swarm.api.routes.events import stream_run_events
from fastapi import Request

@pytest.mark.anyio
async def test_stream_run_events_traversal():
    """Test that stream_run_events validates run_id against path traversal."""
    # Setup
    mock_manager = MagicMock()
    # Use current directory as root
    mock_manager.runs_root = Path.cwd()

    mock_request = MagicMock(spec=Request)
    mock_request.is_disconnected.return_value = False

    # Mock dependencies
    with patch("swarm.api.server.get_spec_manager", return_value=mock_manager):
        with patch("swarm.runtime.resilient_db.check_db_health"):

            # The test expects ValueError because validate_path_component throws ValueError on ".."
            with pytest.raises(ValueError, match="traversal sequence"):
                await stream_run_events(run_id="..", request=mock_request)

            with pytest.raises(ValueError, match="invalid characters"):
                await stream_run_events(run_id="../etc", request=mock_request)
