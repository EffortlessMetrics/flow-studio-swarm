import pytest
from pathlib import Path
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from swarm.api.server import create_app

@pytest.fixture
def mock_run_env(tmp_path):
    """Setup a temporary run environment with a secret file outside the run directory."""
    # Structure:
    # tmp_path/swarm/runs/test-run
    # tmp_path/swarm/runs/secret_location/handoff/secret.json

    repo_root = tmp_path
    swarm_dir = repo_root / "swarm"
    runs_dir = swarm_dir / "runs"
    runs_dir.mkdir(parents=True)

    run_id = "test-run"
    run_path = runs_dir / run_id
    run_path.mkdir()

    # Create a secret file in a sibling directory that mimics the structure
    # ../secret_location/handoff/secret.json
    secret_dir = runs_dir / "secret_location" / "handoff"
    secret_dir.mkdir(parents=True)

    # Add assumptions_made to secret file so it shows up in aggregation if read
    secret_data = {
        "assumptions_made": [
            {
                "assumption_id": "secret-1",
                "statement": "The secret is Found me!",
                "rationale": "It was unprotected",
                "impact_if_wrong": "Critical",
                "confidence": "high",
                "status": "active"
            }
        ]
    }
    secret_file = secret_dir / "secret.json"
    secret_file.write_text(json.dumps(secret_data))

    return run_path, repo_root

def test_boundary_traversal_blocked(mock_run_env):
    """Assert that the vulnerability is blocked (regression test)."""
    run_path, repo_root = mock_run_env
    run_id = run_path.name

    # Patch find_run_path to return our temp run path
    with patch("swarm.api.routes.boundary.find_run_path", return_value=run_path):
        app = create_app(repo_root=repo_root)
        client = TestClient(app)

        # The attack payload: try to traverse to sibling directory
        flow_key = "../secret_location"

        response = client.get(f"/api/runs/{run_id}/boundary-review?flow_key={flow_key}")

        # Expect 400 Bad Request
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}: {response.text}"

        # Check error message
        detail = response.json().get("detail", {})
        msg = str(detail)
        assert "contains invalid characters" in msg or "traversal sequence" in msg or "invalid_flow_key" in msg
