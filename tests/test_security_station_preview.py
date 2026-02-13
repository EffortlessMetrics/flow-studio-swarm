
import pytest
from fastapi.testclient import TestClient
from swarm.tools.flow_studio.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_station_compile_preview_path_traversal_run_id(client):
    """Test that path traversal in run_id is rejected."""
    payload = {
        "flow_id": "3-build",
        "step_id": "3.3",
        "station_id": "code-implementer",
        "run_id": "../../../etc/passwd"
    }

    response = client.post("/api/station/compile-preview", json=payload)

    assert response.status_code == 400
    # validate_path_component raises ValueError with specific messages
    # e.g., "run_id contains invalid characters: ..."
    error_msg = response.json()["error"]
    assert "contains invalid characters" in error_msg or "traversal sequence" in error_msg

def test_station_compile_preview_path_traversal_flow_id(client):
    """Test that path traversal in flow_id is rejected."""
    payload = {
        "flow_id": "../../../etc/passwd",
        "step_id": "3.3",
        "station_id": "code-implementer",
        "run_id": "default"
    }

    response = client.post("/api/station/compile-preview", json=payload)

    assert response.status_code == 400
    error_msg = response.json()["error"]
    assert "contains invalid characters" in error_msg or "traversal sequence" in error_msg

def test_station_compile_preview_path_traversal_step_id(client):
    """Test that path traversal in step_id is rejected."""
    payload = {
        "flow_id": "3-build",
        "step_id": "../../../etc/passwd",
        "station_id": "code-implementer",
        "run_id": "default"
    }

    response = client.post("/api/station/compile-preview", json=payload)

    assert response.status_code == 400
    error_msg = response.json()["error"]
    assert "contains invalid characters" in error_msg or "traversal sequence" in error_msg
