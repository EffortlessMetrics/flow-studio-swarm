import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, Request

# Import the handler
from swarm.api.routes.events import stream_run_events


@pytest.mark.anyio
async def test_stream_run_events_traversal_vulnerability():
    """
    Test that stream_run_events detects path traversal attempts.
    Before the fix, this test should fail (vulnerability confirmed).
    After the fix, it should pass (validation error caught).
    """

    # Mock dependencies
    with patch("swarm.api.server.get_spec_manager") as mock_get_manager, \
         patch("swarm.runtime.resilient_db.check_db_health"):

        # Setup mock manager
        mock_manager = MagicMock()
        mock_manager.runs_root = Path("/tmp/runs")
        mock_get_manager.return_value = mock_manager

        # Mock request
        mock_request = MagicMock(spec=Request)
        mock_request.is_disconnected.return_value = False

        # Malicious run_id
        malicious_run_id = "../etc/passwd"

        # Execute handler
        try:
            await stream_run_events(malicious_run_id, mock_request)
        except HTTPException as e:
            # If it raises 400, it's fixed/validated.
            if e.status_code == 400:
                return  # PASS - Validated correctly

            # If it raises 404, it means it tried to look up the file (traversal successful but file not found)
            if e.status_code == 404:
                pytest.fail(
                    "VULNERABILITY CONFIRMED: Function attempted to access path (returned 404) instead of rejecting invalid run_id (400)."
                )

            raise e
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")

        # If it didn't raise anything (unlikely given 404 check logic in code), fail
        pytest.fail("Function did not raise HTTPException.")
