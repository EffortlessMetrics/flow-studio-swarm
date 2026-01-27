import os
from unittest import mock
from swarm.utils.cors import get_cors_origins

class TestCorsConfig:
    def test_default_origins(self):
        """Test default origins when env var is not set."""
        # Ensure SWARM_ALLOWED_ORIGINS is not set
        with mock.patch.dict(os.environ, {}, clear=True):
            # We need to ensure we don't accidentally inherit the env var if it was set in the real env
            # The clear=True does this for the duration of the context
            origins = get_cors_origins()
            assert "http://localhost:5000" in origins
            assert "http://localhost:5001" in origins
            assert "http://127.0.0.1:5000" in origins
            assert len(origins) == 4

    def test_override_origins(self):
        """Test overriding origins with env var."""
        with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": "https://example.com, https://api.example.com"}):
            origins = get_cors_origins()
            assert "https://example.com" in origins
            assert "https://api.example.com" in origins
            assert len(origins) == 2

    def test_allow_all(self):
        """Test allowing all origins."""
        with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": "*"}):
            origins = get_cors_origins()
            assert origins == ["*"]

    def test_disable_cors(self):
        """Test disabling CORS (empty list)."""
        with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": ""}):
            origins = get_cors_origins()
            assert origins == []

    def test_whitespace_handling(self):
        """Test handling of whitespace in env var."""
        with mock.patch.dict(os.environ, {"SWARM_ALLOWED_ORIGINS": " http://a.com , http://b.com "}):
            origins = get_cors_origins()
            assert "http://a.com" in origins
            assert "http://b.com" in origins
