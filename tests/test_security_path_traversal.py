from fastapi.testclient import TestClient
from swarm.tools.flow_studio_fastapi import app

client = TestClient(app)

def test_transcript_invalid_chars_flow_key():
    """Test that invalid chars in flow_key are rejected."""
    # '$' is not in the allowlist
    response = client.get("/api/runs/run1/flows/flow$key/steps/step1/transcript")
    assert response.status_code == 400
    assert "Invalid path component" in response.json()["error"]

def test_transcript_invalid_chars_step_id():
    """Test that invalid chars in step_id are rejected."""
    # ' ' (space) is not in the allowlist
    response = client.get("/api/runs/run1/flows/flow1/steps/step%201/transcript")
    assert response.status_code == 400
    assert "Invalid path component" in response.json()["error"]

def test_transcript_invalid_chars_run_id():
    """Test that invalid chars in run_id are rejected."""
    # '!' is not in the allowlist
    response = client.get("/api/runs/run!1/flows/flow1/steps/step1/transcript")
    assert response.status_code == 400
    assert "Invalid path component" in response.json()["error"]
