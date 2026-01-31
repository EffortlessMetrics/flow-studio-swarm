"""
Security tests for Database API endpoints.

Tests for path traversal and input validation on DB routes.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
from swarm.api.server import create_app
from swarm.runtime.storage import EVENTS_FILE

def test_db_rebuild_traversal_prevention(tmp_path):
    """Test that path traversal attempts in rebuild endpoint are caught."""
    # Setup
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    runs_dir = repo_root / "swarm" / "runs"
    runs_dir.mkdir(parents=True)

    # Create a secret directory outside runs_dir
    secret_dir = repo_root / "swarm" / "secret"
    secret_dir.mkdir()

    # Create a malicious events file (just in case it bypasses validation)
    event = {
        "event": "secret_accessed",
        "timestamp": "2024-01-01T00:00:00Z",
        "data": "you_should_not_see_this"
    }

    with open(secret_dir / EVENTS_FILE, "w") as f:
        f.write(json.dumps(event) + "\n")

    # Initialize app with mocked repo_root
    app = create_app(repo_root=repo_root, enable_cors=False)
    client = TestClient(app)

    # Payload for rebuild with path traversal
    payload = {
        "run_ids": ["../secret", "valid-run"],
        "force": True
    }

    response = client.post("/api/db/rebuild", json=payload)

    # Should return 200 (partial success/failure report)
    assert response.status_code == 200
    data = response.json()

    # Check errors
    errors = data.get("errors", [])
    assert len(errors) > 0, "Expected errors in response"

    traversal_error = next((e for e in errors if e.get("run_id") == "../secret"), None)
    assert traversal_error is not None, "Expected error for invalid run_id"

    error_msg = traversal_error.get("error", "")
    # Should be rejected by validate_path_component
    assert "traversal sequence" in error_msg or "invalid characters" in error_msg

def test_db_ingest_validation(tmp_path):
    """Test that ingest endpoint validates run_id."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    app = create_app(repo_root=repo_root, enable_cors=False)
    client = TestClient(app)

    # "bad$id" contains '$' which is invalid in validate_path_component
    response = client.post("/api/db/ingest/bad$id")

    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("error") == "validation_error"
    assert "contains invalid characters" in detail.get("message", "")

def test_db_ingest_valid_id(tmp_path):
    """Test that ingest endpoint accepts valid run_id."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    app = create_app(repo_root=repo_root, enable_cors=False)
    client = TestClient(app)

    # "valid-id_123" is valid
    response = client.post("/api/db/ingest/valid-id_123")

    assert response.status_code == 200
    # ResilientDB returns success=True even if no events file (empty projection)
    assert response.json().get("success") is True
