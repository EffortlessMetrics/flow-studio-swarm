"""Tests for CORS configuration security.

These tests verify that the API and UI servers enforce strict CORS policies,
preventing unauthorized cross-origin access.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from swarm.api.server import create_app as create_api_app
from swarm.tools.flow_studio.app import create_app as create_ui_app


class TestCORSSecurity:
    """Security tests for CORS configuration."""

    def test_api_cors_defaults(self):
        """Verify API server defaults to strict localhost origins."""
        # Create app with default settings
        app = create_api_app()
        client = TestClient(app)

        # Test allowed origin
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5000"}
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5000"

        # Test blocked origin (should not return allow-origin header)
        response = client.get(
            "/api/health",
            headers={"Origin": "http://evil.com"}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_ui_cors_defaults(self):
        """Verify UI server defaults to strict localhost origins."""
        # Create app with default settings
        app = create_ui_app()
        client = TestClient(app)

        # Test allowed origin
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5000"}
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5000"

        # Test blocked origin
        response = client.get(
            "/api/health",
            headers={"Origin": "http://evil.com"}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_custom_allowed_origins(self):
        """Verify that SWARM_ALLOWED_ORIGINS env var works."""
        custom_origin = "https://trusted-domain.com"

        with patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": custom_origin}):
            # Test API
            app = create_api_app()
            client = TestClient(app)

            response = client.get(
                "/api/health",
                headers={"Origin": custom_origin}
            )
            assert response.headers["access-control-allow-origin"] == custom_origin

            # Test UI
            app = create_ui_app()
            client = TestClient(app)

            response = client.get(
                "/api/health",
                headers={"Origin": custom_origin}
            )
            assert response.headers["access-control-allow-origin"] == custom_origin
