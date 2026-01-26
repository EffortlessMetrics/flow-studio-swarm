"""
test_cors_config.py - Tests for CORS configuration utility.
"""

import os
from unittest.mock import patch

import pytest
from swarm.utils.cors import get_cors_origins


@pytest.mark.unit
def test_get_cors_origins_defaults():
    """Test default CORS origins."""
    with patch.dict(os.environ, {}, clear=True):
        origins = get_cors_origins()
        assert "http://localhost:5000" in origins
        assert "http://127.0.0.1:5000" in origins
        assert "http://localhost:5001" in origins
        assert "http://127.0.0.1:5001" in origins
        assert len(origins) == 4


@pytest.mark.unit
def test_get_cors_origins_override():
    """Test environment variable override."""
    with patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": "https://example.com, https://api.example.com"}):
        origins = get_cors_origins()
        assert "https://example.com" in origins
        assert "https://api.example.com" in origins
        assert len(origins) == 2


@pytest.mark.unit
def test_get_cors_origins_wildcard():
    """Test wildcard override."""
    with patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": "*"}):
        origins = get_cors_origins()
        assert origins == ["*"]


@pytest.mark.unit
def test_get_cors_origins_empty():
    """Test empty override (disable CORS origins)."""
    with patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": ""}):
        origins = get_cors_origins()
        assert origins == []

    with patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": "   "}):
        origins = get_cors_origins()
        assert origins == []
