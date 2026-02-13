from fastapi.testclient import TestClient
from swarm.tools.flow_studio.app import create_app
import pytest

# Initialize client outside test to share app state if possible,
# but create_app might need to be called per test or module.
# Using module scope fixture is better if startup is heavy, but here it's fine.
client = TestClient(create_app())

def test_station_preview_path_traversal():
    """Test that station preview endpoint rejects path traversal."""

    # Test flow_id traversal
    response = client.post(
        "/api/station/compile-preview",
        json={
            "flow_id": "../../../ux_manifest",
            "step_id": "step1",
            "station_id": "station1",
            "run_id": "default"
        }
    )
    assert response.status_code == 400
    error_msg = response.json()["error"]
    assert "contains invalid characters" in error_msg or "traversal sequence" in error_msg
    assert "flow_id" in error_msg

    # Test step_id traversal
    response = client.post(
        "/api/station/compile-preview",
        json={
            "flow_id": "valid_flow",
            "step_id": "../step1",
            "station_id": "station1",
            "run_id": "default"
        }
    )
    assert response.status_code == 400
    error_msg = response.json()["error"]
    assert "contains invalid characters" in error_msg or "traversal sequence" in error_msg
    assert "step_id" in error_msg

    # Test run_id traversal
    response = client.post(
        "/api/station/compile-preview",
        json={
            "flow_id": "valid_flow",
            "step_id": "step1",
            "station_id": "station1",
            "run_id": "../../etc"
        }
    )
    assert response.status_code == 400
    error_msg = response.json()["error"]
    assert "contains invalid characters" in error_msg or "traversal sequence" in error_msg
    assert "run_id" in error_msg

def test_station_preview_valid_ids():
    """Test that valid IDs are accepted (even if spec not found)."""

    response = client.post(
        "/api/station/compile-preview",
        json={
            "flow_id": "non_existent_flow",
            "step_id": "step1",
            "station_id": "station1",
            "run_id": "valid-run-id"
        }
    )

    # We expect 404 because the flow doesn't exist, but inputs are valid
    assert response.status_code == 404
    error_msg = response.json()["error"]
    assert "Spec not found" in error_msg

    # Ensure it's not a validation error
    assert "contains invalid characters" not in error_msg
