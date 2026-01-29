
import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_rebuild_database_path_traversal_prevention(client):
    """Test that path traversal attempts in rebuild_database are blocked."""

    with patch("swarm.runtime.resilient_db.get_resilient_db") as mock_get_db:
        mock_db_instance = MagicMock()
        mock_get_db.return_value = mock_db_instance

        with patch("swarm.runtime.resilient_db.check_db_health"):
            mock_db_instance.health.healthy = True
            mock_db_instance.health.needs_rebuild = False
            mock_db_instance.rebuild_from_events_safe.return_value = {"success": True}

            payload = {
                "run_ids": ["../etc/passwd", "valid-run-id"],
                "force": True
            }

            response = client.post("/api/db/rebuild", json=payload)

            assert response.status_code == 200
            data = response.json()

            # The invalid run ID should be in errors
            errors = data.get("errors", [])
            # We expect errors to be present.
            # ../etc/passwd fails validation "traversal sequence"
            assert any(e["run_id"] == "../etc/passwd" for e in errors)

            # The backend should NOT have been called with the invalid ID
            # It should have been called ONCE with the valid ID
            mock_db_instance.rebuild_from_events_safe.assert_called_once_with("valid-run-id")

def test_ingest_run_events_path_traversal_prevention(client):
    """Test that path traversal attempts in ingest_run_events are blocked."""

    with patch("swarm.runtime.resilient_db.get_resilient_db") as mock_get_db:
        mock_db_instance = MagicMock()
        mock_get_db.return_value = mock_db_instance
        mock_db_instance.rebuild_from_events_safe.return_value = {"success": True}

        # Use a character that is invalid but won't cause 404 due to path splitting
        # '$' is invalid per validate_path_component
        response = client.post("/api/db/ingest/bad$id")

        data = response.json()
        assert data.get("success") is False
        assert "invalid characters" in data.get("error", "")

        # Ensure backend was NOT called
        mock_db_instance.rebuild_from_events_safe.assert_not_called()

def test_stream_run_events_path_traversal_prevention(client):
    """Test that path traversal attempts in stream_run_events are blocked."""

    # Use a character that is invalid but won't cause 404 due to path splitting
    response = client.get("/api/runs/bad$id/events")

    # Should be 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "invalid_run_id"
