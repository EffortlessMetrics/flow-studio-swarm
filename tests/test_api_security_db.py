
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from swarm.api.server import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_rebuild_database_path_traversal(client):
    """Test that rebuild_database is vulnerable to path traversal (reproduction)."""
    with patch("swarm.runtime.resilient_db.get_resilient_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Setup mock behavior
        mock_db.health.healthy = True
        mock_db.health.needs_rebuild = False
        mock_db.rebuild_from_events_safe.return_value = {"success": True}

        # Payload with path traversal
        payload = {"run_ids": ["../etc/passwd"], "force": True}

        response = client.post("/api/db/rebuild", json=payload)

        # Should NOT call mock with bad ID
        # Should return success=True (partial success or overall success depends on logic,
        # but here we focus on security: mock not called)

        assert response.status_code == 200
        # Check that rebuild_from_events_safe was NOT called
        mock_db.rebuild_from_events_safe.assert_not_called()

        # Check that the error was recorded
        data = response.json()
        assert len(data["errors"]) == 1
        assert "traversal sequence" in data["errors"][0]["error"] or "invalid characters" in data["errors"][0]["error"]

def test_ingest_run_events_path_traversal(client):
    """Test that ingest_run_events is protected against path traversal."""
    # Note: TestClient resolves '..', so we test with invalid characters that are NOT path separators
    # but strictly disallowed by validate_path_component (e.g. '$')

    with patch("swarm.runtime.resilient_db.get_resilient_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.rebuild_from_events_safe.return_value = {"success": True}

        # validate_path_component regex is ^[a-zA-Z0-9_\-\.]+$
        # So 'invalid$id' should be rejected.

        run_id = "invalid$id"
        response = client.post(f"/api/db/ingest/{run_id}")

        # Should be 400 Bad Request
        assert response.status_code == 400
        assert "invalid_run_id" in response.json()["detail"]["error"]

        # Mock should NOT be called
        mock_db.rebuild_from_events_safe.assert_not_called()
