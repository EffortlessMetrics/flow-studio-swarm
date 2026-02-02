#!/usr/bin/env python3
"""
API Security Tests for Flow Studio.

Tests path traversal and other security validations in API endpoints.

## Test Coverage

1. test_db_ingest_path_traversal - /api/db/ingest/{run_id} rejects path traversal
2. test_db_rebuild_path_traversal - /api/db/rebuild rejects path traversal in run_ids
3. test_evolution_get_patches_path_traversal - /api/evolution/{run_id} rejects traversal
4. test_evolution_get_detail_path_traversal - /api/evolution/{run_id}/{patch_id} rejects traversal
5. test_evolution_validate_path_traversal - /api/evolution/{run_id}/validate/{patch_id} rejects traversal
6. test_evolution_apply_path_traversal - /api/evolution/apply rejects traversal in patch_id
7. test_evolution_reject_path_traversal - /api/evolution/{run_id}/reject/{patch_id} rejects traversal
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

@pytest.fixture
def fastapi_client():
    """Create FastAPI test client."""
    # We need to mock get_resilient_db because app creation initializes it
    # and we don't want to create real DB files or fail if they don't exist
    with patch("swarm.runtime.resilient_db.get_resilient_db") as mock_db:
        mock_db_instance = MagicMock()
        mock_db_instance.health.healthy = True
        mock_db_instance.health.projection_version = 2
        mock_db_instance.health.rebuild_count = 0
        mock_db_instance.health.last_error = None
        mock_db.return_value = mock_db_instance

        from swarm.api.server import create_app
        app = create_app()
        return TestClient(app)

def test_db_ingest_path_traversal(fastapi_client):
    """Test /api/db/ingest/{run_id} rejects path traversal and invalid chars."""
    # Use invalid characters that pass routing but fail validation
    # Allowed: alphanumeric, _, -, .
    # Invalid: *, @, space, etc.
    invalid_ids = ["run*id", "run id", "run@id"]

    for run_id in invalid_ids:
        resp = fastapi_client.post(f"/api/db/ingest/{run_id}")
        assert resp.status_code == 400, f"Expected 400 for run_id={run_id}, got {resp.status_code}"
        data = resp.json()
        # FastAPI returns detail object
        assert data["detail"]["error"] == "invalid_run_id"
        assert "run_id" in data["detail"]["details"]

    # Valid ID should proceed
    # Patch swarm.runtime.resilient_db.get_resilient_db because api/routes/db.py imports it inside function
    # but we can also patch it where it is defined.
    with patch("swarm.runtime.resilient_db.get_resilient_db") as mock_db_getter:
        mock_db = MagicMock()
        mock_db.rebuild_from_events_safe.return_value = {"success": True}
        mock_db_getter.return_value = mock_db

        resp = fastapi_client.post("/api/db/ingest/valid-run-id")
        assert resp.status_code == 200

def test_db_rebuild_path_traversal(fastapi_client):
    """Test /api/db/rebuild rejects path traversal in run_ids."""
    # Request with invalid run_id
    payload = {
        "run_ids": ["valid-run", "../secret"],
        "force": False
    }

    with patch("swarm.runtime.resilient_db.get_resilient_db") as mock_db_getter:
        mock_db = MagicMock()
        mock_db.health.healthy = True
        mock_db.rebuild_from_events_safe.return_value = {"success": True}
        mock_db_getter.return_value = mock_db

        resp = fastapi_client.post("/api/db/rebuild", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Check that errors contain the invalid run_id
        errors = data["errors"]
        assert len(errors) > 0
        error_entry = next((e for e in errors if e.get("run_id") == "../secret"), None)
        assert error_entry is not None
        # The error message comes from validate_path_component
        assert "invalid characters" in error_entry["error"] or "traversal" in error_entry["error"]

def test_evolution_get_patches_path_traversal(fastapi_client):
    """Test /api/evolution/{run_id} rejects traversal/invalid chars."""
    invalid_ids = ["run*id"]

    for run_id in invalid_ids:
        resp = fastapi_client.get(f"/api/evolution/{run_id}")
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["error"] == "invalid_run_id"

def test_evolution_get_detail_path_traversal(fastapi_client):
    """Test /api/evolution/{run_id}/{patch_id} rejects traversal/invalid chars."""
    # Invalid run_id
    resp = fastapi_client.get("/api/evolution/run*id/patch-id")
    assert resp.status_code == 400

    # Invalid patch_id
    resp = fastapi_client.get("/api/evolution/valid-run/patch*id")
    assert resp.status_code == 400

def test_evolution_validate_path_traversal(fastapi_client):
    """Test /api/evolution/{run_id}/validate/{patch_id} rejects traversal/invalid chars."""
    # Invalid run_id
    resp = fastapi_client.post("/api/evolution/run*id/validate/patch-id")
    assert resp.status_code == 400

    # Invalid patch_id
    resp = fastapi_client.post("/api/evolution/valid-run/validate/patch*id")
    assert resp.status_code == 400

def test_evolution_apply_path_traversal(fastapi_client):
    """Test /api/evolution/apply rejects traversal in patch_id."""

    # Case 1: patch_id with colon (run_id:patch_id)
    payload = {
        "patch_id": "../secret:patch-id",
        "dry_run": True
    }
    resp = fastapi_client.post("/api/evolution/apply", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "invalid_patch_id"

    payload = {
        "patch_id": "valid-run:../patch-id",
        "dry_run": True
    }
    resp = fastapi_client.post("/api/evolution/apply", json=payload)
    assert resp.status_code == 400

    # Case 2: patch_id without colon (just patch_id)
    payload = {
        "patch_id": "../patch-id",
        "dry_run": True
    }
    resp = fastapi_client.post("/api/evolution/apply", json=payload)
    assert resp.status_code == 400

def test_evolution_reject_path_traversal(fastapi_client):
    """Test /api/evolution/{run_id}/reject/{patch_id} rejects traversal/invalid chars."""
    payload = {"reason": "bad patch", "patch_id": "ignored"} # patch_id in body is for request model but endpoint uses url

    # Invalid run_id
    resp = fastapi_client.post("/api/evolution/run*id/reject/patch-id", json=payload)
    assert resp.status_code == 400

    # Invalid patch_id
    resp = fastapi_client.post("/api/evolution/valid-run/reject/patch*id", json=payload)
    assert resp.status_code == 400
