
import pytest
from fastapi.testclient import TestClient
from swarm.tools.flow_studio.app import create_app as create_flow_studio_app
from swarm.api.server import create_app as create_spec_api_app

def test_flow_studio_cors_restricted():
    app = create_flow_studio_app()
    client = TestClient(app)

    # 1. Verify restricted origin (should be REJECTED)
    headers = {"Origin": "http://evil.com"}
    response = client.get("/api/health", headers=headers)

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers, "Flow Studio: Should not allow evil.com"

    # 2. Verify allowed origin
    headers = {"Origin": "http://localhost:5000"}
    response = client.get("/api/health", headers=headers)

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5000"

def test_spec_api_cors_restricted():
    app = create_spec_api_app()
    client = TestClient(app)

    # 1. Verify restricted origin (should be REJECTED)
    headers = {"Origin": "http://evil.com"}
    # spec api health is at /api/health
    response = client.get("/api/health", headers=headers)

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers, "Spec API: Should not allow evil.com"

    # 2. Verify allowed origin
    headers = {"Origin": "http://localhost:5001"}
    response = client.get("/api/health", headers=headers)

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5001"

def test_env_var_override(monkeypatch):
    monkeypatch.setenv("SWARM_ALLOWED_ORIGINS", "http://good.example.com, http://also.good.com")

    # Re-create app to pick up env var
    app = create_flow_studio_app()
    client = TestClient(app)

    headers = {"Origin": "http://good.example.com"}
    response = client.get("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://good.example.com"
