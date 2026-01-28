
import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_db_rebuild_traversal(client):
    """Test that rebuilding with a path traversal run_id returns an error in the response."""
    # This tests the JSON body which IS vulnerable to traversal (slashes allowed in string)
    # Must use force=True to bypass the early return when DB is healthy
    response = client.post("/api/db/rebuild", json={"run_ids": ["../sensitive"], "force": True})

    assert response.status_code == 200
    data = response.json()

    errors = data.get("errors", [])
    assert len(errors) > 0

    found_validation_error = False
    for error in errors:
        err_msg = str(error.get("error", ""))
        if "traversal sequence" in err_msg or "invalid characters" in err_msg:
            found_validation_error = True
            break

    assert found_validation_error, f"Expected validation error, got: {errors}"

def test_db_ingest_invalid_chars(client):
    """Test that ingesting with invalid characters in run_id fails with 400."""
    # Use 'invalid$id' which has no slashes (so matches route) but has invalid char '$'
    response = client.post("/api/db/ingest/invalid$id")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "invalid characters" in detail

def test_events_stream_invalid_chars(client):
    """Test that streaming events with invalid characters fails with 400."""
    # Use 'invalid$id'
    response = client.get("/api/runs/invalid$id/events")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "invalid characters" in detail
