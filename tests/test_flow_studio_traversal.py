
import pytest
from fastapi.testclient import TestClient
from swarm.tools.flow_studio_fastapi import app

def test_api_station_compile_preview_path_traversal():
    """Verify that path traversal is blocked in compile-preview endpoint."""
    client = TestClient(app)

    # Payload with path traversal in run_id
    payload = {
        "run_id": "../../etc",
        "flow_id": "1-signal",
        "step_id": "normalize",
        "station_id": "dummy"
    }

    response = client.post("/api/station/compile-preview", json=payload)

    # We expect 400 Bad Request
    assert response.status_code == 400

    error_msg = response.json().get("error", "")
    assert "traversal sequence" in error_msg or "invalid characters" in error_msg
