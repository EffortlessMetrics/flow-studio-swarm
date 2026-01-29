import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app
from unittest.mock import MagicMock, patch

@pytest.fixture
def client(tmp_path):
    # Mock swarm.runtime.db.get_stats_db to prevent real DB creation issues
    with patch("swarm.runtime.db.get_stats_db"), \
         patch("swarm.runtime.resilient_db.get_resilient_db") as mock_get_res_db:

        mock_db = MagicMock()
        mock_db.health.healthy = True
        mock_db.health.needs_rebuild = False
        # Make rebuild_from_events_safe return a dummy success
        mock_db.rebuild_from_events_safe.return_value = {"success": True, "events_ingested": 10}

        mock_get_res_db.return_value = mock_db

        app = create_app(repo_root=tmp_path)
        client = TestClient(app)
        client.mock_db = mock_db
        yield client

def test_db_rebuild_path_traversal(client):
    """
    Test that path traversal in run_ids is rejected and recorded as an error.
    """
    payload = {
        "run_ids": ["../etc/passwd", "valid_run"],
        "force": True
    }

    response = client.post("/api/db/rebuild", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Check that errors were reported for the bad ID
    errors = data.get("errors", [])
    assert len(errors) > 0
    # The error message comes from validate_path_component
    assert any("traversal sequence" in str(e) for e in errors) or \
           any("invalid characters" in str(e) for e in errors)

    # Check that the bad ID was NOT passed to the DB
    # The mock tracks all calls. "valid_run" should be called, "../etc/passwd" should not.
    calls = [args[0] for args, _ in client.mock_db.rebuild_from_events_safe.call_args_list]
    assert "valid_run" in calls
    assert "../etc/passwd" not in calls

def test_ingest_run_events_path_traversal(client):
    """Test that path traversal in ingest endpoint raises 400."""
    # Using a character that is invalid (space) to test validation
    # This confirms validate_path_component is being called.
    response = client.post("/api/db/ingest/bad%20run")
    assert response.status_code == 400
    assert "invalid characters" in response.json()["detail"]["message"]

def test_events_stream_path_traversal(client):
    """Test that path traversal in events endpoint raises 400."""
    # Using a character that is invalid (space) to test validation
    response = client.get("/api/runs/bad%20run/events")
    assert response.status_code == 400
    assert "invalid characters" in response.json()["detail"]["message"]
