import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add repo root to path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from swarm.api import create_app

@pytest.fixture
def client(tmp_path):
    # Create app with temporary repo root to avoid affecting real files
    app = create_app(repo_root=tmp_path)
    return TestClient(app)

def test_events_run_id_validation(client):
    """Test that invalid run_id is rejected in events endpoint."""
    # Test characters that are invalid but don't break URL routing like slashes
    invalid_ids = ["invalid$id", "back\\slash", "space id"]

    for run_id in invalid_ids:
        response = client.get(f"/api/runs/{run_id}/events")
        assert response.status_code == 400, f"Expected 400 for {run_id}, got {response.status_code}. Resp: {response.text}"

    # Verify a valid ID format (even if run doesn't exist) returns 404 (Not Found) instead of 400
    response = client.get("/api/runs/valid-id/events")
    assert response.status_code == 404, f"Expected 404 for valid-id, got {response.status_code}"

def test_db_ingest_run_id_validation(client):
    """Test that invalid run_id is rejected in db ingest endpoint."""
    invalid_ids = ["invalid$id", "back\\slash", "space id"]

    for run_id in invalid_ids:
        response = client.post(f"/api/db/ingest/{run_id}")
        assert response.status_code == 400, f"Expected 400 for {run_id}, got {response.status_code}. Resp: {response.text}"

def test_evolution_run_id_validation(client):
     """Test that invalid run_id is rejected in evolution endpoint."""
     invalid_ids = ["invalid$id", "back\\slash"]

     for run_id in invalid_ids:
         response = client.get(f"/api/evolution/{run_id}")
         assert response.status_code == 400, f"Expected 400 for {run_id}, got {response.status_code}. Resp: {response.text}"

def test_wisdom_run_id_validation(client):
     """Test that invalid run_id is rejected in wisdom endpoint."""
     invalid_ids = ["invalid$id", "back\\slash"]

     for run_id in invalid_ids:
         response = client.get(f"/api/wisdom/{run_id}")
         assert response.status_code == 400, f"Expected 400 for {run_id}, got {response.status_code}. Resp: {response.text}"
