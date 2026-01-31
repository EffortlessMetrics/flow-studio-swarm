
import pytest
from fastapi.testclient import TestClient
from swarm.api.asgi import app

client = TestClient(app)

def test_path_traversal_events_stream():
    """
    Test that invalid run_id for event stream is rejected.
    """
    # Use characters not in allowlist to trigger validation error
    run_id = "invalid$id"

    response = client.get(f"/api/runs/{run_id}/events")

    print(f"\nEvents Stream Response status: {response.status_code}")
    print(f"Events Stream Response json: {response.json() if response.content else ''}")

    assert response.status_code == 400
    assert response.json()['detail']['error'] == 'invalid_run_id'

def test_path_traversal_db_ingest():
    """
    Test that invalid run_id for db ingest is rejected.
    """
    run_id = "invalid$id"
    response = client.post(f"/api/db/ingest/{run_id}")

    print(f"\nDB Ingest Response status: {response.status_code}")
    print(f"DB Ingest Response json: {response.json() if response.content else ''}")

    assert response.status_code == 400
    assert response.json()['detail']['error'] == 'invalid_run_id'
