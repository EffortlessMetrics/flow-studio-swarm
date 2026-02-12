import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from swarm.tools.flow_studio_fastapi import app

@pytest.fixture
def client():
    return TestClient(app)

def test_api_station_compile_preview_path_traversal_run_id(client):
    """Test that api_station_compile_preview blocks path traversal in run_id."""
    # We mock SpecCompiler to avoid side effects, but we expect validation to block before it
    with patch("swarm.spec.compiler.SpecCompiler") as MockCompiler:
        response = client.post(
            "/api/station/compile-preview",
            json={
                "flow_id": "valid-flow",
                "step_id": "valid-step",
                "station_id": "valid-station",
                "run_id": "../../../../etc/passwd"
            }
        )

        assert response.status_code == 400
        assert "run_id" in response.json()["error"]
        assert not MockCompiler.called

def test_api_station_compile_preview_path_traversal_flow_id(client):
    """Test that api_station_compile_preview blocks path traversal in flow_id."""
    with patch("swarm.spec.compiler.SpecCompiler") as MockCompiler:
        response = client.post(
            "/api/station/compile-preview",
            json={
                "flow_id": "../etc/passwd",
                "step_id": "valid-step",
                "station_id": "valid-station",
                "run_id": "valid-run"
            }
        )

        assert response.status_code == 400
        assert "flow_id" in response.json()["error"]
        assert not MockCompiler.called

def test_api_station_compile_preview_path_traversal_step_id(client):
    """Test that api_station_compile_preview blocks path traversal in step_id."""
    with patch("swarm.spec.compiler.SpecCompiler") as MockCompiler:
        response = client.post(
            "/api/station/compile-preview",
            json={
                "flow_id": "valid-flow",
                "step_id": "../etc/passwd",
                "station_id": "valid-station",
                "run_id": "valid-run"
            }
        )

        assert response.status_code == 400
        assert "step_id" in response.json()["error"]
        assert not MockCompiler.called
