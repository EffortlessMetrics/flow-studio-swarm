from fastapi.testclient import TestClient
from swarm.api.server import create_app
import pytest

# Initialize app for testing
app = create_app(enable_cors=False)
client = TestClient(app)

def test_compile_preview_run_base_traversal():
    """Test that path traversal in run_base is rejected by the API."""

    # Payload with traversal in run_base
    payload = {
        "station_id": "test-station",
        "step_id": "test-step",
        "objective": "Test objective",
        "flow_key": "build",
        "run_base": "../../../etc/passwd"
    }

    response = client.post("/api/compile/preview", json=payload)

    # Should return 422 Unprocessable Entity (validation error)
    assert response.status_code == 422
    data = response.json()

    # Check that error is about run_base
    assert data["detail"][0]["loc"] == ["body", "run_base"]
    # The message might vary slightly depending on Pydantic version and custom validator
    error_msg = data["detail"][0]["msg"]
    assert "traversal sequence" in error_msg or "must be a relative path" in error_msg

def test_compile_preview_run_base_absolute():
    """Test that absolute path in run_base is rejected."""

    payload = {
        "station_id": "test-station",
        "step_id": "test-step",
        "objective": "Test objective",
        "flow_key": "build",
        "run_base": "/etc/passwd"
    }

    response = client.post("/api/compile/preview", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "run_base"]
    assert "must be a relative path" in data["detail"][0]["msg"]

def test_compile_preview_valid_path_structure():
    """Test that a valid path structure is accepted by validation layer.

    Note: This might fail 404 or 400 later because the station doesn't exist,
    but we want to ensure it passes the Pydantic validation (status != 422).
    """

    payload = {
        "station_id": "non-existent-station",
        "step_id": "test-step",
        "objective": "Test objective",
        "flow_key": "build",
        "run_base": "swarm/runs/preview"
    }

    response = client.post("/api/compile/preview", json=payload)

    # If validation passes, it will try to compile and fail with 404 (station not found)
    # or 500 (internal error), but NOT 422.
    assert response.status_code != 422
