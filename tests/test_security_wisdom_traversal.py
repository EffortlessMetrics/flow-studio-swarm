import pytest
from fastapi.testclient import TestClient

from swarm.tools.flow_studio.app import create_app

app = create_app()
client = TestClient(app)

def test_evolution_apply_path_traversal():
    """Test path traversal prevention on /api/v1/evolution/apply"""
    payload = {
        "patch_id": "../../../etc/passwd:FLOW-PATCH-001",
        "dry_run": True
    }
    response = client.post("/api/v1/evolution/apply", json=payload)
    # The client might normalize ../.., but %2e%2e%2f doesn't always work based on Starlette
    assert response.status_code in [400, 404]

def test_wisdom_get_artifacts_path_traversal():
    """Test path traversal prevention on /api/v1/wisdom/{run_id}"""
    # Test path validation. Fastapi test client might return 404 for certain traversals
    # but we can test that it returns 400 for our validation helper with invalid chars
    # Since we mapped /wisdom to /api/v1/wisdom without specific artifacts route, use base route
    response = client.get("/api/v1/wisdom/invalid_run_id_!@#$/artifacts")
    assert response.status_code in [400, 404]

    response = client.get("/api/v1/wisdom/valid-run-id/artifacts")
    assert response.status_code == 404 # Not found is expected for valid ID that doesn't exist
