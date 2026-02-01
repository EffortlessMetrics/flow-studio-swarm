
import pytest
from fastapi.testclient import TestClient
from swarm.api.server import create_app
from swarm.api.services.spec_manager import set_spec_manager, SpecManager

@pytest.fixture
def client(tmp_path):
    set_spec_manager(SpecManager(tmp_path))
    app = create_app(repo_root=tmp_path, enable_cors=False)
    return TestClient(app)

def test_rebuild_database_path_traversal(client):
    """
    Test that providing a path traversal sequence in run_ids to /api/db/rebuild
    is rejected with an error in the response errors list.
    """
    payload = {
        "run_ids": ["../traversal_attempt"],
        "force": True
    }

    response = client.post("/api/db/rebuild", json=payload)

    # It returns 200 OK because it's a partial success/failure batch operation
    assert response.status_code == 200
    data = response.json()

    # Check that errors list contains the validation error
    assert len(data["errors"]) > 0
    error_entry = data["errors"][0]
    assert error_entry["run_id"] == "../traversal_attempt"
    # validate_path_component raises "traversal sequence" for '..'
    # but for '../something' it raises "invalid characters" because of the slash
    assert "traversal sequence" in error_entry["error"] or "invalid characters" in error_entry["error"]

    assert data["success"] is False

def test_ingest_run_events_path_traversal(client):
    """
    Test that providing an invalid path component to /api/db/ingest/{run_id}
    returns 400 Bad Request.
    """
    # We use 'invalid$char' because TestClient/Starlette normalizes '..'
    # and slashes might break route matching.
    # validate_path_component restricts to alphanumeric, _, -, .
    run_id = "invalid$char"

    response = client.post(f"/api/db/ingest/{run_id}")

    assert response.status_code == 400
    assert "invalid characters" in response.json()["detail"]

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path.cwd()))
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        c = client(Path(tmp_dir))
        test_rebuild_database_path_traversal(c)
        test_ingest_run_events_path_traversal(c)
        print("All tests passed!")
