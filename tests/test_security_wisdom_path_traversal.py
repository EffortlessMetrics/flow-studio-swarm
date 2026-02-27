
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from swarm.api.server import create_app
from swarm.api.services.spec_manager import clear_spec_manager, set_spec_manager, SpecManager

@pytest.fixture
def client(tmp_path):
    # Setup directory structure
    swarm_dir = tmp_path / "swarm"
    runs_dir = swarm_dir / "runs"
    runs_dir.mkdir(parents=True)

    # Create a secret file in the runs directory (easier to reach)
    secret_file = runs_dir / "secret.txt"
    secret_file.write_text("This is a secret!")

    # Create a legitimate run directory and wisdom directory
    run_id = "valid-run"
    wisdom_dir = runs_dir / run_id / "wisdom"
    wisdom_dir.mkdir(parents=True)

    # Create a legitimate artifact
    artifact = wisdom_dir / "insight.md"
    artifact.write_text("Some insight")

    # Initialize app with tmp_path as repo_root
    # We need to clear the singleton first to ensure fresh initialization
    clear_spec_manager()

    # Manually initialize SpecManager with our tmp_path to ensure it's used
    manager = SpecManager(repo_root=tmp_path)
    set_spec_manager(manager)

    app = create_app(repo_root=tmp_path)
    return TestClient(app)

def test_wisdom_path_traversal_artifact_name(client):
    """Test that accessing a file outside the wisdom directory via artifact_name returns 400.

    We use invalid characters to trigger the validator without client-side normalization interference.
    The validator explicitly rejects slashes and anything not in [a-zA-Z0-9_\-\.].
    """
    run_id = "valid-run"

    # Use a character not in the allowlist to verify validator is active
    invalid_name = "invalid$name"

    response = client.get(f"/api/wisdom/{run_id}/{invalid_name}")

    # Expect 400 Bad Request due to path validation failure
    assert response.status_code == 400
    assert "invalid_artifact_name" in response.text

def test_wisdom_path_traversal_run_id(client):
    """Test that accessing a file via run_id manipulation returns 400."""
    # Use a character not in the allowlist to verify validator is active
    invalid_run_id = "run$id"

    # Even if we just try to list artifacts, it should fail validation
    response = client.get(f"/api/wisdom/{invalid_run_id}")

    # Expect 400 Bad Request due to run_id validation
    assert response.status_code == 400
    assert "invalid_run_id" in response.text

def test_apply_patch_traversal(client):
    """Test that path traversal in apply patch endpoint returns 400.

    This is the most critical test as the payload is in the body and not normalized by the client.
    """
    run_id = "valid-run"
    # Payload with traversal in artifact_name
    # This string is passed directly to the validator
    payload = {
        "artifact_name": "../../secret.txt",
        "dry_run": True
    }

    response = client.post(f"/api/wisdom/{run_id}/apply", json=payload)

    # Expect 400 Bad Request due to artifact_name validation
    assert response.status_code == 400
    assert "invalid_artifact_name" in response.text
