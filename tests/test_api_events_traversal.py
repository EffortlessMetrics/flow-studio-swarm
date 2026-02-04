import pytest
from fastapi.testclient import TestClient
from swarm.tools.flow_studio_fastapi import app

def test_stream_run_events_traversal_parent():
    """Test that stream_run_events rejects parent directory traversal."""
    client = TestClient(app)

    # Attempt path traversal with encoded ".." (%2e%2e)
    # Before fix: returns 404 (Not Found) because client/server normalizes or finds nothing.
    # After fix: returns 400 (Bad Request) because validate_path_component catches it.
    response = client.get("/api/runs/%2e%2e/events")

    # Should be 400 Bad Request
    assert response.status_code == 400
    assert "traversal sequence" in response.text or "invalid characters" in response.text
