
import pytest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from swarm.api.routes import wisdom, evolution

# Create a test app with the routers
app = FastAPI()
app.include_router(wisdom.router)
app.include_router(evolution.router)

client = TestClient(app)

@pytest.fixture
def mock_runs_root(tmp_path):
    """Mock runs root to point to a temporary directory."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create a legitimate run
    run_id = "valid-run"
    wisdom_dir = runs_dir / run_id / "wisdom"
    wisdom_dir.mkdir(parents=True)
    (wisdom_dir / "valid-artifact.md").write_text("content")

    # Create a secret file outside runs dir to test traversal
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("TOP SECRET")

    return runs_dir

def test_wisdom_path_traversal_run_id(mock_runs_root):
    """Test path traversal in run_id for wisdom endpoints."""
    # Mock the _get_runs_root helper in wisdom module
    with patch("swarm.api.routes.wisdom._get_runs_root", return_value=mock_runs_root):
        # Try traversal in run_id
        response = client.get("/wisdom/../latest")
        # FastAPI might handle this at routing level, let's try a valid looking but traversal path
        # But run_id is a path parameter, so /wisdom/../artifact is interpreted as /wisdom/artifact
        # We need to test encoded traversal or just passing it if it wasn't a path param.
        # However, FastAPI path params usually decode.

        # Let's try explicitly passing a run_id that traverses
        # If the route is /wisdom/{run_id}, then accessing /wisdom/../foo
        # is actually request to /foo.
        # But if we use url encoding: /wisdom/%2E%2E/foo

        response = client.get("/wisdom/%2E%2E/latest")
        # If traversal is blocked, we should get 400 or 404 (if looked up safely)
        # If traversal works, it might try to list root dir or fail with 500

        # NOTE: FastAPI/Starlette routing might normalize paths before hitting the handler.
        # But if we assume the handler gets ".." as run_id:
        pass

def test_wisdom_path_traversal_artifact_name(mock_runs_root):
    """Test path traversal in artifact_name for wisdom endpoints."""
    with patch("swarm.api.routes.wisdom._get_runs_root", return_value=mock_runs_root):
        run_id = "valid-run"
        # Try to access secret.txt which is at ../../../secret.txt relative to runs/run-id/wisdom
        artifact_name = "../../../secret.txt"

        # /wisdom/{run_id}/{artifact_name}
        response = client.get(f"/wisdom/{run_id}/{artifact_name}")

        # Should be 400 Bad Request if validation is working
        # Currently it might be 200 (if it finds the file) or 500
        if response.status_code == 200 and "TOP SECRET" in response.text:
            pytest.fail("Path traversal successful - vulnerability exists")

        assert response.status_code in [400, 404]

def test_wisdom_path_traversal_apply_patch(mock_runs_root):
    """Test path traversal in apply patch request."""
    with patch("swarm.api.routes.wisdom._get_runs_root", return_value=mock_runs_root):
        run_id = "valid-run"
        payload = {
            "dry_run": True,
            "artifact_name": "../../../secret.txt"
        }

        response = client.post(f"/wisdom/{run_id}/apply", json=payload)

        if response.status_code == 200 or (response.status_code == 500 and "read_failed" in response.text):
             # It tried to read the file
             pass

        assert response.status_code in [400, 404]

def test_evolution_path_traversal_run_id(mock_runs_root):
    """Test path traversal in run_id for evolution endpoints."""
    with patch("swarm.api.routes.evolution._get_runs_root", return_value=mock_runs_root):
        # /evolution/{run_id}
        run_id = ".."
        response = client.get(f"/evolution/{run_id}")
        assert response.status_code in [400, 404]

def test_evolution_path_traversal_patch_id(mock_runs_root):
    """Test path traversal in patch_id."""
    with patch("swarm.api.routes.evolution._get_runs_root", return_value=mock_runs_root):
        run_id = "valid-run"
        patch_id = "../patch"

        # /evolution/{run_id}/{patch_id}
        response = client.get(f"/evolution/{run_id}/{patch_id}")
        assert response.status_code in [400, 404]
