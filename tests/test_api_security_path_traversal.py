
import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app
from swarm.api.services.spec_manager import set_spec_manager, SpecManager

@pytest.fixture
def client():
    # Create a fresh app instance for testing
    app = create_app()

    # Initialize SpecManager explicitly just in case create_app's side effect
    # isn't persisted or we want to control it
    set_spec_manager(SpecManager())

    return TestClient(app)

def test_path_traversal_events_stream(client):
    """
    Test that invalid run_id for event stream is rejected.
    """
    # Use characters not in allowlist to trigger validation error
    run_id = "invalid$id"

    response = client.get(f"/api/runs/{run_id}/events")

    # We expect 400 Bad Request due to validation failure
    assert response.status_code == 400
    assert response.json()['detail']['error'] == 'invalid_run_id'

def test_path_traversal_db_ingest(client):
    """
    Test that invalid run_id for db ingest is rejected.
    """
    run_id = "invalid$id"
    response = client.post(f"/api/db/ingest/{run_id}")

    # We expect 400 Bad Request due to validation failure
    assert response.status_code == 400
    assert response.json()['detail']['error'] == 'invalid_run_id'
