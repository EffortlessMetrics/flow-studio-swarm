from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from swarm.api.routes import events


@pytest.mark.anyio
async def test_events_path_traversal():
    """Test that events endpoints validate run_id against path traversal."""

    # Mock runs root
    runs_root = Path("/tmp/runs")
    mock_manager = MagicMock()
    mock_manager.runs_root = runs_root

    # patch get_spec_manager where it is imported in events.py (inside the function)
    # Since it does `from ..server import get_spec_manager`, we should patch `swarm.api.server.get_spec_manager`

    with patch("swarm.api.server.get_spec_manager", return_value=mock_manager):
        # Mock Request
        request = MagicMock(spec=Request)

        # We also need to mock check_db_health to avoid import errors or side effects
        with patch("swarm.runtime.resilient_db.check_db_health"):

            # Test stream_run_events
            try:
                await events.stream_run_events(run_id="../etc", request=request)
                pytest.fail("Should have raised ValueError for traversal in stream_run_events")
            except ValueError as e:
                assert "run_id" in str(e) or "traversal sequence" in str(e)
            except HTTPException:
                pytest.fail("Vulnerable: Traversal allowed in stream_run_events (got 404 instead of ValueError)")
