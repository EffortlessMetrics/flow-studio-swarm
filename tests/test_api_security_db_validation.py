
import pytest
from fastapi.testclient import TestClient
from swarm.api.asgi import app

client = TestClient(app)

def test_db_rebuild_validation():
    """Test that /api/db/rebuild validates run_ids against path traversal."""
    # This payload uses ".." which should be rejected.
    payload = {
        "run_ids": ["valid_run", "../secret"],
        "force": True
    }

    response = client.post("/api/db/rebuild", json=payload)

    # Expect 400 Bad Request due to validation failure
    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    assert "traversal sequence" in response.text or "invalid characters" in response.text

def test_db_ingest_validation():
    """Test that /api/db/ingest/{run_id} validates run_id."""
    # We use characters not allowed in the allowlist (alphanumeric, underscore, hyphen, dot).
    # e.g. '$' or space.

    response = client.post("/api/db/ingest/invalid$run")

    # Should be 400 because "$" is invalid in a path component (run_id)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    assert "invalid characters" in response.text

def test_db_ingest_validation_traversal_sequence():
    """Test that /api/db/ingest/{run_id} validates '..' sequence."""

    # This checks backslash which is definitely invalid and a traversal risk on Windows
    response = client.post("/api/db/ingest/invalid\\run")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    assert "invalid characters" in response.text
