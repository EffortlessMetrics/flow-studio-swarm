import sys
from pathlib import Path

# Add repo root to sys.path to satisfy tests importing from swarm/tools/
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from swarm.api.asgi import app

client = TestClient(app)

def test_get_wisdom_content_path_traversal():
    """Verify that artifact_name is validated to prevent path traversal."""
    # Test valid
    response = client.get("/api/wisdom/run123/good_file.txt")

    # Test invalid with bad characters that don't get normalized
    response2 = client.get("/api/wisdom/run123/bad_file$name")

    assert response2.status_code == 400
    assert "invalid_path_parameter" in response2.text

def test_get_evolution_patch_details_path_traversal():
    """Verify that patch_id is validated to prevent path traversal."""
    response = client.get("/api/evolution/run123/bad_file$name")

    assert response.status_code == 400
    assert "invalid_path_parameter" in response.text
