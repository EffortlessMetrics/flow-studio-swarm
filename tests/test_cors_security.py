
import os
import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app as create_spec_app
from swarm.tools.flow_studio.app import create_app as create_studio_app

def test_spec_api_cors_secure():
    """Verify that Spec API rejects arbitrary origins and allows localhost."""
    app = create_spec_app()
    client = TestClient(app)

    # Evil origin
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET",
        }
    )
    # Should NOT have the header, or should not equal the origin
    assert "access-control-allow-origin" not in response.headers or \
           response.headers["access-control-allow-origin"] != "http://evil.com"

    # Good origin
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5000",
            "Access-Control-Request-Method": "GET",
        }
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5000"


def test_studio_app_cors_secure():
    """Verify that Flow Studio App rejects arbitrary origins."""
    app = create_studio_app()
    client = TestClient(app)

    # Evil origin
    response = client.options(
        "/health",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET",
        }
    )
    # Should NOT have the header, or should not equal the origin
    assert "access-control-allow-origin" not in response.headers or \
           response.headers["access-control-allow-origin"] != "http://evil.com"

    # Good origin
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5001",
            "Access-Control-Request-Method": "GET",
        }
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5001"
