import os
from unittest import mock

from swarm.utils.cors_config import get_allowed_origins


def test_get_allowed_origins_default():
    """Test that default origins are returned when env var is not set."""
    with mock.patch.dict(os.environ, {}, clear=True):
        origins = get_allowed_origins()
        expected = [
            "http://localhost:5000",
            "http://localhost:5001",
            "http://127.0.0.1:5000",
            "http://127.0.0.1:5001",
        ]
        assert sorted(origins) == sorted(expected)


def test_get_allowed_origins_custom():
    """Test that custom origins are returned when env var is set."""
    custom_origins = "https://example.com, https://api.example.com"
    with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": custom_origins}, clear=True):
        origins = get_allowed_origins()
        expected = ["https://example.com", "https://api.example.com"]
        assert sorted(origins) == sorted(expected)


def test_get_allowed_origins_custom_single():
    """Test with a single custom origin."""
    custom_origins = "https://myapp.com"
    with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": custom_origins}, clear=True):
        origins = get_allowed_origins()
        expected = ["https://myapp.com"]
        assert origins == expected


def test_get_allowed_origins_whitespace():
    """Test that whitespace is handled correctly."""
    custom_origins = "  http://a.com , http://b.com  "
    with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": custom_origins}, clear=True):
        origins = get_allowed_origins()
        expected = ["http://a.com", "http://b.com"]
        assert sorted(origins) == sorted(expected)


def test_get_allowed_origins_empty_string():
    """Test empty string results in empty list or fallback? Code says fallback only if env var is None or missing.
    Actually if it is set but empty, splitting empty string might result in [''] which we filter out.
    """
    with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": ""}, clear=True):
        origins = get_allowed_origins()
        # If set to empty string, it enters the if block but returns empty list because of split
        assert origins == []
