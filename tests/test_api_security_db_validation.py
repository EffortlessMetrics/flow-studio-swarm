
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from swarm.api.server import create_app

@pytest.fixture
def mock_db():
    mock = MagicMock()
    mock.health.healthy = True
    mock.health.needs_rebuild = False
    mock.rebuild_from_events_safe.return_value = {
        "success": True,
        "events_ingested": 10
    }
    return mock

@pytest.fixture
def client(mock_db):
    # Patch get_resilient_db to return our mock
    with patch("swarm.runtime.resilient_db.get_resilient_db", return_value=mock_db), \
         patch("swarm.runtime.resilient_db.check_db_health"):
        app = create_app()
        client = TestClient(app)
        yield client

def test_ingest_run_events_validation(client, mock_db):
    """Test that /db/ingest/{run_id} validates the run_id."""

    # Valid ID
    response = client.post("/api/db/ingest/valid-id_123")
    assert response.status_code == 200
    mock_db.rebuild_from_events_safe.assert_called_with("valid-id_123")

    mock_db.reset_mock()

    # Invalid ID (invalid character)
    response = client.post("/api/db/ingest/bad$id")
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_input"
    assert not mock_db.rebuild_from_events_safe.called

    # Invalid ID (traversal characters)
    # Note: TestClient resolves .. but we can try other chars or encoded ones if needed.
    # But since we use validate_path_component, checking one invalid char is enough
    # to prove the validator is invoked.

def test_rebuild_database_validation(client, mock_db):
    """Test that /db/rebuild validates run_ids in the list."""

    # Mix of valid and invalid IDs
    payload = {
        "run_ids": ["valid-1", "bad$id", "valid-2"],
        "force": True
    }

    response = client.post("/api/db/rebuild", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Check stats
    # 2 valid runs should be processed
    assert data["runs_processed"] == 2
    # 1 error should be reported
    assert len(data["errors"]) == 1
    assert data["errors"][0]["run_id"] == "bad$id"
    assert "invalid characters" in data["errors"][0]["error"]

    # Check mock calls
    assert mock_db.rebuild_from_events_safe.call_count == 2
    mock_db.rebuild_from_events_safe.assert_any_call("valid-1")
    mock_db.rebuild_from_events_safe.assert_any_call("valid-2")

    # Ensure it wasn't called with the bad one
    call_args_list = [c[0][0] for c in mock_db.rebuild_from_events_safe.call_args_list]
    assert "bad$id" not in call_args_list
