#!/usr/bin/env python3
"""
Makefile backend toggle tests - ARCHIVED.

Flask backend has been archived. These tests are retained for historical reference
but are now skipped. The Makefile flow-studio target uses FastAPI only.

Original purpose: Test environment variable-based backend selection for Flow Studio.

## Test Coverage (7 tests - ALL SKIPPED)

1. test_makefile_flow_studio_target_exists - flow-studio target exists in Makefile
2. test_makefile_default_backend - Default backend is Flask (no env var)
3. test_makefile_flask_backend - FLOWSTUDIO_BACKEND=flask uses Flask
4. test_makefile_fastapi_backend - FLOWSTUDIO_BACKEND=fastapi uses FastAPI
5. test_makefile_env_var_overrides - Environment variable properly overrides default
6. test_makefile_syntax_valid - Makefile syntax is valid (dry-run)
7. test_both_backends_start - Both backends start without errors
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest


@pytest.fixture
def repo_root_path():
    """Get repository root path."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def makefile_path(repo_root_path):
    """Get Makefile path."""
    return repo_root_path / "Makefile"


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_makefile_flow_studio_target_exists(makefile_path):
    """Test flow-studio target exists in Makefile."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_makefile_default_backend(makefile_path, repo_root_path):
    """Test default backend is Flask (no env var set)."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_makefile_flask_backend(makefile_path, repo_root_path):
    """Test FLOWSTUDIO_BACKEND=flask explicitly uses Flask."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_makefile_fastapi_backend(makefile_path, repo_root_path):
    """Test FLOWSTUDIO_BACKEND=fastapi explicitly uses FastAPI."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_makefile_env_var_overrides(makefile_path, repo_root_path):
    """Test environment variable properly overrides default."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_makefile_syntax_valid(makefile_path, repo_root_path):
    """Test Makefile syntax is valid (dry-run mode)."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_both_backends_start():
    """Test both backends can be imported without errors."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_makefile_both_serve_port_5000(makefile_path, repo_root_path):
    """Test both backends serve on http://localhost:5000."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - backend toggle removed")
def test_makefile_fastapi_reload_enabled(repo_root_path):
    """Test FastAPI backend has --reload flag for development."""
    pass  # Flask backend archived
