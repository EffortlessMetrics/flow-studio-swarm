import os
from unittest import mock
import pytest
from swarm.utils.cors_config import get_cors_origins, DEFAULT_ALLOWED_ORIGINS

@pytest.mark.unit
def test_default_origins():
    """Test that default origins are returned when env var is not set."""
    with mock.patch.dict(os.environ, {}, clear=True):
        assert get_cors_origins() == DEFAULT_ALLOWED_ORIGINS

@pytest.mark.unit
def test_custom_origins():
    """Test that env var overrides default origins."""
    custom = "http://example.com,https://app.example.com"
    with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": custom}, clear=True):
        origins = get_cors_origins()
        assert "http://example.com" in origins
        assert "https://app.example.com" in origins
        assert len(origins) == 2

@pytest.mark.unit
def test_disable_cors():
    """Test that empty string allows no origins (effectively disabling CORS if logic uses this list)."""
    with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": ""}, clear=True):
        assert get_cors_origins() == []

@pytest.mark.unit
def test_whitespace_handling():
    """Test that whitespace is handled correctly."""
    custom = " http://example.com , http://test.com "
    with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": custom}, clear=True):
        origins = get_cors_origins()
        assert "http://example.com" in origins
        assert "http://test.com" in origins
        assert len(origins) == 2
