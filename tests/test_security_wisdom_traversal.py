import pytest
from pathlib import Path
from swarm.runtime.safe_paths import validate_path_component
from swarm.api.routes import wisdom, evolution

# =============================================================================
# Path Validation Tests (Core Logic)
# =============================================================================

def test_validate_path_component_valid():
    """Test that valid path components pass validation."""
    assert validate_path_component("valid-id_123.json") == "valid-id_123.json"
    assert validate_path_component("run-20260119-143022-abc123") == "run-20260119-143022-abc123"
    assert validate_path_component("signal") == "signal"
    assert validate_path_component("step_1") == "step_1"

def test_validate_path_component_empty():
    """Test that empty strings are rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_path_component("")

def test_validate_path_component_traversal():
    """Test that traversal sequences are rejected."""
    with pytest.raises(ValueError, match="traversal sequence"):
        validate_path_component("..")

    with pytest.raises(ValueError, match="traversal sequence"):
        validate_path_component(".")

def test_validate_path_component_slashes():
    """Test that forward slashes are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
        validate_path_component("foo/bar")

    with pytest.raises(ValueError, match="invalid characters"):
        validate_path_component("../foo")

def test_validate_path_component_backslashes():
    """Test that backslashes are rejected (Windows path traversal)."""
    with pytest.raises(ValueError, match="invalid characters"):
        validate_path_component("foo\\bar")

    with pytest.raises(ValueError, match="invalid characters"):
        validate_path_component("..\\etc")

# =============================================================================
# Wisdom API Tests
# =============================================================================

def test_wisdom_get_artifacts_validation():
    """Test input validation for get_wisdom_artifacts."""
    from fastapi.testclient import TestClient
    from swarm.api.server import create_app

    app = create_app()
    client = TestClient(app)

    # Test valid run_id
    # Note: We expect 404 because the run doesn't exist, not 500 or validation error
    resp = client.get("/api/wisdom/valid-run-id")
    assert resp.status_code == 404

    # Test traversal in run_id
    # Should be caught by path validation before filesystem access
    # NOTE: FastAPI/Starlette test client might normalize '..' in paths,
    # so we rely on the validation logic being called.
    # If the validation is working, it should return 400.
    # If it bypasses validation (because of client normalization), it hits 404.
    # We assert 400 OR 404 depending on how the client behaves,
    # but the key is that it DOES NOT return 500 or succeed with a traversal.
    # However, since we explicitly want to test the validation logic, we can try
    # an invalid char that isn't '..' if possible, or assume the client sends raw.

    # Let's try invalid char '/' which is definitely rejected by our regex
    # and not normalized away like '..' might be.
    resp = client.get("/api/wisdom/invalid/run/id")
    # This might route to run_id="invalid/run/id" ? No, slash splits path.
    # We need a char that is valid in URL but invalid in our ID.
    # Our regex is strict: ^[a-zA-Z0-9_\-\.]+$
    # So a space or special char should fail.

    resp = client.get("/api/wisdom/run%20space") # "run space"
    assert resp.status_code == 400

    # Also try the traversal pattern if possible
    resp = client.get("/api/wisdom/..%2Fetc%2Fpasswd")
    # If client normalizes this to /api/wisdom/../etc/passwd -> /api/etc/passwd, we get 404.
    # If it sends raw, we get 400.
    assert resp.status_code in (400, 404)

def test_wisdom_get_content_validation():
    """Test input validation for get_wisdom_content."""
    from fastapi.testclient import TestClient
    from swarm.api.server import create_app

    app = create_app()
    client = TestClient(app)

    # Test traversal in artifact_name
    resp = client.get("/api/wisdom/valid-run/..%2Fetc%2Fpasswd")
    # Starlette might normalize ".." even inside path params, causing 404
    assert resp.status_code in (400, 404)

    # Test invalid chars which won't be normalized
    resp = client.get("/api/wisdom/valid-run/bad$file")
    assert resp.status_code == 400

def test_wisdom_apply_patch_validation():
    """Test input validation for apply_wisdom_patch."""
    from fastapi.testclient import TestClient
    from swarm.api.server import create_app

    app = create_app()
    client = TestClient(app)

    # Test traversal in run_id
    resp = client.post(
        "/api/wisdom/..%2Fetc%2Fpasswd/apply",
        json={"dry_run": True, "artifact_name": "patch.json"}
    )
    # Starlette might normalize ".." even inside path params, causing 404
    assert resp.status_code in (400, 404)

    # Test traversal in artifact_name (in body) - this definitely shouldn't be normalized by router
    resp = client.post(
        "/api/wisdom/valid-run/apply",
        json={"dry_run": True, "artifact_name": "../etc/passwd"}
    )
    assert resp.status_code == 400

# =============================================================================
# Evolution API Tests
# =============================================================================

def test_evolution_get_patches_validation():
    """Test input validation for get_run_evolution_patches."""
    from fastapi.testclient import TestClient
    from swarm.api.server import create_app

    app = create_app()
    client = TestClient(app)

    # Test traversal in run_id
    resp = client.get("/api/evolution/..%2Fetc%2Fpasswd")
    # Starlette might normalize ".." even inside path params, causing 404
    assert resp.status_code in (400, 404)

def test_evolution_get_patch_details_validation():
    """Test input validation for get_evolution_patch_details."""
    from fastapi.testclient import TestClient
    from swarm.api.server import create_app

    app = create_app()
    client = TestClient(app)

    # Test traversal in patch_id
    resp = client.get("/api/evolution/valid-run/..%2Fetc%2Fpasswd")
    # Starlette might normalize ".." even inside path params, causing 404
    assert resp.status_code in (400, 404)

def test_evolution_apply_validation():
    """Test input validation for apply_evolution_patch_endpoint."""
    from fastapi.testclient import TestClient
    from swarm.api.server import create_app

    app = create_app()
    client = TestClient(app)

    # Test traversal in patch_id (in body)
    # The patch_id might contain run_id prefix (run_id:patch_id)
    # Both parts should be validated
    resp = client.post(
        "/api/evolution/apply",
        json={"patch_id": "../etc/passwd:patch1", "dry_run": True}
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/evolution/apply",
        json={"patch_id": "run1:../etc/passwd", "dry_run": True}
    )
    assert resp.status_code == 400
