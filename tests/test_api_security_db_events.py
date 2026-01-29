import pytest
from fastapi.testclient import TestClient
from swarm.api import create_app

# Create app instance for testing
app = create_app()
client = TestClient(app)

def test_db_ingest_invalid_chars():
    """Test invalid characters in /api/db/ingest/{run_id}."""
    # Use space which is invalid in validate_path_component but valid in URL path segment
    resp = client.post("/api/db/ingest/foo%20bar")

    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "invalid characters" in resp.json()["detail"]["message"]

def test_db_rebuild_path_traversal():
    """Test path traversal in /api/db/rebuild run_ids."""
    path = "../" * 4 + "etc/passwd"
    resp = client.post("/api/db/rebuild", json={
        "run_ids": [path],
        "force": True
    })

    assert resp.status_code == 200
    data = resp.json()

    # Verify we catch it and report it in errors list
    assert len(data["errors"]) > 0
    error_msg = data["errors"][0]["error"]

    # Can be "traversal sequence" or "invalid characters" depending on which check hits first
    assert "traversal sequence" in error_msg or "invalid characters" in error_msg

def test_events_stream_invalid_chars():
    """Test invalid characters in /api/runs/{run_id}/events."""
    # Use space which is invalid
    resp = client.get("/api/runs/foo%20bar/events")

    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "invalid characters" in resp.json()["detail"]["message"]
