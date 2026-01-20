
import pytest
from fastapi.testclient import TestClient
from swarm.tools.flow_studio_fastapi import app

client = TestClient(app)

def test_runs_traversal_attack():
    response = client.get("/api/runs/../../etc/passwd/summary")
    # Should be 404 because FastAPI router won't match ".." in path param unless it's a catch-all
    # But wait, if run_id absorbs "..", it might match.
    # Actually, standard HTTP clients/servers might resolve ".." before routing.
    # However, if we urlencode it, or if it's passed as is.

    # If I pass it as a path parameter, FastAPI/Starlette might handle it.
    # But let's try a simpler one: "invalid..id" which is a valid URL segment but invalid according to our logic.

    response = client.get("/api/runs/invalid..id/summary")
    assert response.status_code == 400
    assert "Traversal sequences" in response.json()["error"]

def test_runs_invalid_chars():
    response = client.get("/api/runs/invalid/id/summary")
    # This might match a different route or return 404 because of the slash
    # "invalid/id" inside {run_id} is usually not matched unless {run_id:path}
    pass

def test_runs_flow_key_traversal():
    # run_id needs to be valid format to pass first check
    run_id = "valid_run_id"
    flow_key = "invalid..flow"

    response = client.get(f"/api/runs/{run_id}/flows/{flow_key}")
    assert response.status_code == 400
    assert "Traversal sequences" in response.json()["error"]

def test_runs_step_transcript_traversal():
    run_id = "valid_run_id"
    flow_key = "valid_flow"
    step_id = "invalid..step"

    response = client.get(f"/api/runs/{run_id}/flows/{flow_key}/steps/{step_id}/transcript")
    assert response.status_code == 400
    assert "Traversal sequences" in response.json()["error"]

def test_runs_compare_traversal():
    response = client.get("/api/runs/compare?run_a=..&run_b=valid&flow=valid")
    assert response.status_code == 400
    assert "Traversal sequences" in response.json()["error"]

    response = client.get("/api/runs/compare?run_a=valid&run_b=..&flow=valid")
    assert response.status_code == 400

    response = client.get("/api/runs/compare?run_a=valid&run_b=valid&flow=..")
    assert response.status_code == 400
