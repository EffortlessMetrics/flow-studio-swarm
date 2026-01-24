import os
import pytest
from unittest import mock
from fastapi.testclient import TestClient
from swarm.api.server import create_app as create_api_app
from swarm.tools.flow_studio.app import create_app as create_studio_app

def test_api_cors_default():
    """Test default CORS settings for API server."""
    # Ensure env var is not set
    with mock.patch.dict(os.environ, {}, clear=True):
        app = create_api_app()
        client = TestClient(app)

        # Test allowed origin (localhost:5000)
        response = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5000", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5000"

        # Test disallowed origin
        response = client.options(
            "/api/health",
            headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "GET"}
        )
        # If not allowed, FastAPI/Starlette CORS middleware typically doesn't send the header
        assert "access-control-allow-origin" not in response.headers

def test_studio_cors_default():
    """Test default CORS settings for Flow Studio app."""
    with mock.patch.dict(os.environ, {}, clear=True):
        app = create_studio_app()
        client = TestClient(app)

        # Test allowed origin (localhost:5001)
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:5001", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5001"

        # Test disallowed origin
        response = client.options(
            "/health",
            headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "GET"}
        )
        assert "access-control-allow-origin" not in response.headers

def test_api_cors_env_var():
    """Test SWARM_ALLOWED_ORIGINS environment variable."""
    with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": "http://example.com,http://test.com"}):
        app = create_api_app()
        client = TestClient(app)

        # Test allowed origin from env
        response = client.options(
            "/api/health",
            headers={"Origin": "http://example.com", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://example.com"

        # Test default origin (should be disallowed now if env var is set)
        response = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5000", "Access-Control-Request-Method": "GET"}
        )
        assert "access-control-allow-origin" not in response.headers
