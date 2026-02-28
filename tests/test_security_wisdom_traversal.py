"""
Tests for path traversal vulnerabilities in Wisdom and Evolution API routes.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from swarm.api.routes import evolution, wisdom
from swarm.api.routes.validation_utils import _validate_path_param

# Setup a test app including the routers
app = FastAPI()
app.include_router(wisdom.router)
app.include_router(evolution.router)

# Ensure the app doesn't strip or normalize our encoded testing path elements
app.router.redirect_slashes = False

# Mock SpecManager so _get_runs_root doesn't crash on invalid traversal
@pytest.fixture(autouse=True)
def mock_spec_manager(monkeypatch, tmp_path):
    from swarm.api.server import SpecManager, set_spec_manager
    manager = SpecManager(tmp_path)
    set_spec_manager(manager)
    yield
    # reset not strictly necessary but good practice
    set_spec_manager(None)

client = TestClient(app)

# The TestClient automatically normalizes paths like "../", so we need to pass invalid characters
# directly or use testing methods that don't normalize URLs.
# We will test the validation function directly, and then test the endpoints with illegal characters (like slashes)
# to ensure the 400 is raised properly by FastAPI/Starlette when they are not normalized out.

def test_validation_utils_rejects_traversal():
    """Test the core validation utility rejects traversal attempts."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _validate_path_param("..", "run_id")
    assert exc.value.status_code == 400
    assert "traversal sequence" in exc.value.detail["message"]

    with pytest.raises(HTTPException) as exc:
        _validate_path_param("foo/bar", "run_id")
    assert exc.value.status_code == 400
    assert "invalid characters" in exc.value.detail["message"]

def test_wisdom_endpoints_path_traversal():
    """Test that wisdom endpoints reject invalid path parameters."""
    # The TestClient normalizes path slashes and `%2F`, so we use `invalid*path`
    # to bypass the router's normalization and hit the `_validate_path_param` logic.

    # test GET /wisdom/{run_id}
    # In FastAPI TestClient, the router prefix is included.
    # Wisdom prefix is `/wisdom`
    response = client.get("/wisdom/invalid*path")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}. Content: {response.text}"
    assert response.json()["detail"]["error"] == "invalid_path_parameter"

    # test GET /wisdom/{run_id}/{artifact_name}
    response = client.get("/wisdom/valid-run/invalid*artifact.md")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}. Content: {response.text}"

    # test POST /wisdom/{run_id}/apply
    response = client.post("/wisdom/invalid*path/apply", json={"artifact_name": "test.md", "dry_run": True})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}. Content: {response.text}"

def test_evolution_endpoints_path_traversal():
    """Test that evolution endpoints reject invalid path parameters."""

    # test GET /evolution/{run_id}
    response = client.get("/evolution/invalid*path")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}. Content: {response.text}"
    assert response.json()["detail"]["error"] == "invalid_path_parameter"

    # test GET /evolution/{run_id}/{patch_id}
    response = client.get("/evolution/valid-run/invalid*patch")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}. Content: {response.text}"

    # test POST /evolution/{run_id}/validate/{patch_id}
    response = client.post("/evolution/valid-run/validate/invalid*patch")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}. Content: {response.text}"

    # test POST /evolution/apply
    # the patch_id is in the request body, but it is validated inside the endpoint
    response = client.post("/evolution/apply", json={"patch_id": "invalid*patch", "dry_run": True})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}. Content: {response.text}"

    # test POST /evolution/{run_id}/reject/{patch_id}
    response = client.post("/evolution/valid-run/reject/invalid*patch", json={"reason": "test", "patch_id": "invalid*patch"})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}. Content: {response.text}"
