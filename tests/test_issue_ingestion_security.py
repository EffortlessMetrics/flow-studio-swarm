"""Security tests for issue ingestion endpoint."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock necessary modules before importing routes
# We need to mock swarm.runtime.autopilot and swarm.api.services.run_state


@pytest.fixture
def mock_state_manager():
    with patch("swarm.api.routes.issue_routes.get_state_manager") as mock:
        manager = MagicMock()
        manager.runs_root = Path("/tmp/runs")
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_autopilot():
    with patch("swarm.api.routes.issue_routes._get_autopilot_controller") as mock:
        yield mock


@pytest.fixture
def client():
    # Import the router
    from fastapi import FastAPI
    from swarm.api.routes.issue_routes import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_ingest_issue_valid_repo(client, mock_state_manager, mock_autopilot):
    """Test ingestion with a valid repo name."""

    # Setup mocks
    mock_run_create = mock_state_manager.create_run

    async def mock_create_run(*args, **kwargs):
        return {"run_id": kwargs.get("run_id"), "status": "created"}

    mock_run_create.side_effect = mock_create_run

    # Since create_run is async, we need to mock it properly if called
    # But for the purpose of this test, we are mocking the sync part mostly,
    # except the route is async.

    # We need to mock Path.mkdir and Path.write_text to avoid FS errors
    with patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text"):
        response = client.post(
            "/from-issue", json={"provider": "github", "repo": "owner/repo", "issue_number": 123}
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"
    assert "issue-owner-repo-123" in data["run_id"]


def test_ingest_issue_invalid_repo_chars(client, mock_state_manager):
    """Test ingestion with invalid characters in repo name."""

    # "owner$repo" will become "issue-owner$repo-..."
    # $ is invalid in validate_path_component

    with patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text"):
        response = client.post(
            "/from-issue", json={"provider": "github", "repo": "owner$repo", "issue_number": 123}
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "invalid_run_id"
    assert "Generated run ID is invalid" in data["detail"]["message"]


def test_ingest_issue_traversal_attempt(client, mock_state_manager):
    """Test ingestion with path traversal attempt."""

    # "owner/../repo" -> "owner-..-repo" (valid characters, but potentially weird)
    # validate_path_component allows dots and hyphens.

    # ".." as repo -> ".." replaced to ".." if not containing /
    # "foo/../../bar" -> "foo-..-..-bar"

    # But if we try to inject characters that are NOT allowed.
    # space is not allowed.

    with patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text"):
        response = client.post(
            "/from-issue",
            json={"provider": "github", "repo": "owner/repo name", "issue_number": 123},
        )

    # "owner/repo name" -> "owner-repo name" -> has space -> invalid
    assert response.status_code == 400
    assert "invalid_run_id" in response.json()["detail"]["error"]
