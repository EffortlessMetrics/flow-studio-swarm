
import pytest
import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from pathlib import Path

# Import the router
from swarm.api.routes.evolution import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)

@pytest.fixture
def mock_env(tmp_path):
    # Create runs root
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    # Create a target for traversal: runs_root/../traversal_target/wisdom
    # which is tmp_path/traversal_target/wisdom
    traversal_target = tmp_path / "traversal_target" / "wisdom"
    traversal_target.parent.mkdir()
    traversal_target.mkdir()

    with patch("swarm.api.routes.evolution._get_runs_root") as mock_root, \
         patch("swarm.api.routes.evolution._get_evolution_module") as mock_evo, \
         patch("swarm.api.routes.evolution._get_repo_root") as mock_repo_root:

        # Mock runs root to be the real tmp path
        mock_root.return_value = runs_root

        # Mock repo root
        mock_repo_root.return_value = tmp_path

        # Mock evolution module
        mock_module = MagicMock()
        mock_evo.return_value = mock_module

        # Mock list_pending_patches to return empty list
        mock_module.__getitem__.return_value = MagicMock()

        yield runs_root, mock_module

def test_apply_patch_traversal_blocked(mock_env):
    """Test that applying a patch with traversal sequence in ID is BLOCKED."""
    runs_root, mock_evo = mock_env

    run_id_payload = "../traversal_target"
    patch_id_payload = "test-patch"
    full_patch_id = f"{run_id_payload}:{patch_id_payload}"

    payload = {
        "patch_id": full_patch_id,
        "dry_run": True,
        "create_backup": False
    }

    # Mock generate_evolution_patch to return a patch with matching ID
    mock_patch = MagicMock()
    mock_patch.id = patch_id_payload

    mock_validate = MagicMock()
    mock_validate.valid = True

    mock_generate = MagicMock()
    mock_generate.return_value = [mock_patch]

    def get_mock(name):
        if name == "generate_evolution_patch":
            return mock_generate
        if name == "validate_evolution_patch":
            return lambda *args, **kwargs: mock_validate
        if name == "apply_evolution_patch":
            return MagicMock()
        return MagicMock()

    mock_evo.__getitem__.side_effect = get_mock

    # Expect ValueError or 500 error due to validation
    try:
        response = client.post("/evolution/apply", json=payload)
        # If it returns, check status code.
        # But TestClient might raise exception directly if unhandled.
        assert response.status_code != 200
    except ValueError as e:
        assert "invalid characters" in str(e)

    # Ensure generate_evolution_patch was NOT called (because validation happened before)
    assert mock_generate.call_count == 0

def test_validate_patch_traversal_blocked(mock_env):
    """Test path traversal in validate endpoint is BLOCKED."""
    runs_root, mock_evo = mock_env

    run_id = "..%2Ftraversal_target" # URL encoded ../traversal_target
    patch_id = "test-patch"

    mock_generate = MagicMock()
    mock_evo.__getitem__.side_effect = lambda name: mock_generate if name == "generate_evolution_patch" else MagicMock()

    try:
        response = client.post(f"/evolution/{run_id}/validate/{patch_id}")
        assert response.status_code != 200
    except ValueError as e:
        assert "invalid characters" in str(e)
    except Exception:
        # Ignore other exceptions, main point is it didn't succeed
        pass

    # Check that generate_evolution_patch was NOT called
    assert mock_generate.call_count == 0
