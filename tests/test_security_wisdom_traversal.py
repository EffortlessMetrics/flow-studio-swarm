"""
test_security_wisdom_traversal.py - Security tests for Path Traversal in Wisdom/Evolution APIs

Tests that application-level path validation correctly rejects malicious traversal attempts
even if FastAPI's client-side path normalization passes them through (e.g., via URL encoding).
"""

import pytest
from fastapi.testclient import TestClient
from swarm.api.asgi import app

client = TestClient(app)

# Test vectors representing path traversal attempts
# Standard ".." may be caught by Starlette/FastAPI's router matching, returning 404,
# but we also want to verify that backslashes and encoded components are rejected
# securely with a 400 Bad Request if they bypass initial normalization.
TRAVERSAL_PAYLOADS = [
    "../passwd",
    "..%2fpasswd",
    "foo/bar",
    "foo\\bar",
    "foo%5cbar",
    "..",
    ".",
]

@pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
def test_wisdom_artifacts_traversal(payload: str):
    """Test get_wisdom_artifacts rejects traversal in run_id."""
    response = client.get(f"/api/v3/wisdom/{payload}")

    # Depending on how the TestClient standardizes, it might 404 or 400.
    # What we strictly require is that it does NOT return a 500 or successfully
    # read outside the bounds. Because we added the validation explicitly,
    # the ones that route to the endpoint should return 400.
    assert response.status_code in (400, 404)
    if response.status_code == 400:
        data = response.json()
        assert "invalid_path_component" in data["detail"]["error"]


@pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
def test_wisdom_content_run_id_traversal(payload: str):
    """Test get_wisdom_content rejects traversal in run_id."""
    response = client.get(f"/api/v3/wisdom/{payload}/some_artifact.md")
    assert response.status_code in (400, 404)
    if response.status_code == 400:
        data = response.json()
        assert "invalid_path_component" in data["detail"]["error"]


@pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
def test_wisdom_content_artifact_name_traversal(payload: str):
    """Test get_wisdom_content rejects traversal in artifact_name."""
    # We use a valid run_id here
    response = client.get(f"/api/v3/wisdom/valid_run_123/{payload}")
    assert response.status_code in (400, 404)
    if response.status_code == 400:
        data = response.json()
        assert "invalid_path_component" in data["detail"]["error"]


@pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
def test_evolution_patches_traversal(payload: str):
    """Test get_run_evolution_patches rejects traversal in run_id."""
    response = client.get(f"/api/v3/evolution/runs/{payload}")
    assert response.status_code in (400, 404)
    if response.status_code == 400:
        data = response.json()
        assert "invalid_path_component" in data["detail"]["error"]


@pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
def test_evolution_patch_details_patch_id_traversal(payload: str):
    """Test get_evolution_patch_details rejects traversal in patch_id."""
    response = client.get(f"/api/v3/evolution/runs/valid_run_123/patches/{payload}")
    assert response.status_code in (400, 404)
    if response.status_code == 400:
        data = response.json()
        assert "invalid_path_component" in data["detail"]["error"]
