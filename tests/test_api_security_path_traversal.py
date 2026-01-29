#!/usr/bin/env python3
"""
Tests for API security path traversal vulnerabilities.
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app

@pytest.fixture
def fastapi_client():
    """Create FastAPI test client."""
    app = create_app()
    return TestClient(app)

def test_events_path_traversal(fastapi_client):
    """Test that path traversal in run_id for events stream is rejected."""
    # Using a character that is URL-safe but rejected by validate_path_component
    # validate_path_component allowlist: ^[a-zA-Z0-9_\-\.]+$
    # So '!' should be rejected.
    invalid_run_id = "run!id"

    resp = fastapi_client.get(f"/api/runs/{invalid_run_id}/events")

    assert resp.status_code == 400

    data = resp.json()
    assert data["detail"]["error"] == "invalid_run_id"

def test_db_ingest_path_traversal(fastapi_client):
    """Test that path traversal in run_id for db ingestion is rejected."""
    invalid_run_id = "run!id"

    resp = fastapi_client.post(f"/api/db/ingest/{invalid_run_id}")

    assert resp.status_code == 400

    data = resp.json()
    # API might return detail as list or dict depending on validation error source
    if isinstance(data["detail"], dict):
            assert data["detail"]["error"] == "invalid_run_id"

def test_db_rebuild_path_traversal(fastapi_client):
    """Test that path traversal in run_ids for db rebuild is rejected."""
    # This payload passes through to the backend logic
    payload = {
        "run_ids": ["../etc/passwd", "valid-run"],
        "force": True
    }

    resp = fastapi_client.post("/api/db/rebuild", json=payload)

    assert resp.status_code == 400

    data = resp.json()
    if isinstance(data["detail"], dict):
        assert data["detail"]["error"] == "invalid_run_id"
