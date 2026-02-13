#!/usr/bin/env python3
"""
Security tests for station preview endpoint.

Tests that the /api/station/compile-preview endpoint properly validates
input paths to prevent path traversal vulnerabilities.
"""

import pytest
from fastapi.testclient import TestClient
from swarm.tools.flow_studio_fastapi import app

@pytest.fixture
def client():
    return TestClient(app)

def test_compile_preview_path_traversal_run_id(client):
    """Test that path traversal in run_id is rejected."""
    payload = {
        "flow_id": "3-build",
        "step_id": "implement",
        "station_id": "code-implementer",
        "run_id": "../etc/passwd"
    }
    response = client.post("/api/station/compile-preview", json=payload)

    # Should return 400 Bad Request due to validation failure
    assert response.status_code == 400
    error_msg = response.json().get("error", "")
    assert "traversal sequence" in error_msg or "invalid characters" in error_msg

def test_compile_preview_path_traversal_flow_id(client):
    """Test that path traversal in flow_id is rejected."""
    payload = {
        "flow_id": "../../../etc/passwd",
        "step_id": "implement",
        "station_id": "code-implementer",
        "run_id": "default"
    }
    response = client.post("/api/station/compile-preview", json=payload)

    assert response.status_code == 400
    error_msg = response.json().get("error", "")
    assert "traversal sequence" in error_msg or "invalid characters" in error_msg

def test_compile_preview_path_traversal_step_id(client):
    """Test that path traversal in step_id is rejected."""
    payload = {
        "flow_id": "3-build",
        "step_id": "../implement",
        "station_id": "code-implementer",
        "run_id": "default"
    }
    response = client.post("/api/station/compile-preview", json=payload)

    assert response.status_code == 400
    error_msg = response.json().get("error", "")
    assert "traversal sequence" in error_msg or "invalid characters" in error_msg
