
import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app
from swarm.runtime import storage

@pytest.fixture
def client(tmp_path):
    # Setup temporary repo root
    repo_root = tmp_path
    (repo_root / "swarm/runs").mkdir(parents=True)

    app = create_app(repo_root=repo_root)
    return TestClient(app)

def test_db_rebuild_traversal_protection(client):
    """Test that DB rebuild rejects traversal paths."""
    malicious_payload = "../../malicious_run"

    response = client.post("/api/db/rebuild", json={
        "run_ids": [malicious_payload],
        "force": True
    })

    assert response.status_code == 400
    assert "run_id" in response.json()["detail"]

def test_db_ingest_traversal_protection(client):
    """Test that DB ingest rejects traversal paths."""
    # Note: TestClient normalizes paths, so we can't easily test path params like /api/db/ingest/../../foo
    # But we can try to rely on the fact that if it *did* get through, it would hit our validation.
    # Here we just verify we didn't break valid usage or return 500.

    # We can't really test traversal via path param with TestClient easily.
    # But we can verify it returns 404 for a non-existent run, not 500.
    response = client.post("/api/db/ingest/valid-run-id")
    # Should be 200 (success dict with false) or similar, but since we didn't create the run/db,
    # it might fail gracefully.

    # Actually, validate_path_component is called first.
    # If we pass "valid-run-id", it passes validation, then hits db logic.
    assert response.status_code == 200 or response.status_code == 404

    # If we pass invalid char, it should be 400.
    response = client.post("/api/db/ingest/invalid/run/id") # TestClient normalizes this to valid path segments...

    # Try invalid chars that are not path separators, e.g. space or something if validate_path_component checks allowed chars.
    # validate_path_component uses VALID_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
    # So "bad run" should fail.

    response = client.post("/api/db/ingest/bad%20run")
    assert response.status_code == 400
    assert "contains invalid characters" in response.json()["detail"]

def test_evolution_apply_traversal_protection(client):
    """Test that Evolution apply rejects traversal in body."""
    payload = "../../malicious_run:flow_evolution.patch"

    response = client.post("/api/evolution/apply", json={
        "patch_id": payload,
        "dry_run": True
    })

    assert response.status_code == 400
    assert "run_id" in response.json()["detail"]

def test_wisdom_apply_patches_traversal_protection(client):
    """Test that Wisdom apply-patches rejects traversal via path param."""
    # Test invalid chars since we can't test traversal
    response = client.post("/api/wisdom/bad%20run/apply-patches", json={
        "patch_type": "flow_evolution",
        "policy": "safe"
    })
    assert response.status_code == 400
    assert "contains invalid characters" in response.json()["detail"]

def test_events_stream_traversal_protection(client):
    """Test that Events stream rejects invalid chars."""
    response = client.get("/api/runs/bad%20run/events")
    assert response.status_code == 400
    assert "contains invalid characters" in response.json()["detail"]
