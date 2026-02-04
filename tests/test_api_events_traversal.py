import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app
from swarm.api.services.spec_manager import set_spec_manager, SpecManager
from pathlib import Path
import os

@pytest.fixture
def api_client(tmp_path):
    # Setup mock SpecManager
    manager = SpecManager(repo_root=tmp_path)
    set_spec_manager(manager)

    # Create required directories so 404 isn't just "dir not found"
    (tmp_path / "runs").mkdir()

    app = create_app(repo_root=tmp_path)
    return TestClient(app)

def test_stream_run_events_traversal_blocked(api_client):
    """
    Test that the stream_run_events endpoint in swarm/api/routes/events.py
    BLOCKS path traversal with 400 Bad Request.
    """
    # The endpoint is at /api/runs/{run_id}/events
    # We use %2e%2e for .. to try to traverse out of runs_root

    response = api_client.get("/api/runs/%2e%2e/events")

    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")

    # We expect 400 Bad Request because of validation error
    assert response.status_code == 400

    # Check the error message
    # We expect {"detail": {"error": "validation_error", "message": "..."}}
    data = response.json()
    assert "detail" in data
    assert data["detail"]["error"] == "validation_error"
    assert "traversal sequence" in data["detail"]["message"]

def test_stream_run_events_valid_allowed(api_client):
    """Test that valid run_ids are still allowed."""
    response = api_client.get("/api/runs/valid-id/events")

    # Should be 404 (run_not_found) because run doesn't exist,
    # BUT NOT 400 (validation error).
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "run_not_found"
