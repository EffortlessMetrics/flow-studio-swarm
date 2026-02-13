import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from swarm.api.server import create_app
from swarm.api.services.run_state import RunStateManager, get_state_manager
from swarm.api.services.spec_manager import SpecManager

@pytest.fixture
def mock_fs(tmp_path):
    """Setup mock filesystem for runs."""
    runs_dir = tmp_path / "swarm" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir

@pytest.fixture
def client(mock_fs):
    """Create test client with mocked state manager."""
    # Mock SpecManager to return our temp path
    mock_spec_mgr = MagicMock(spec=SpecManager)
    mock_spec_mgr.runs_root = mock_fs
    mock_spec_mgr.repo_root = mock_fs.parent.parent

    # Create StateManager with our temp path
    state_manager = RunStateManager(mock_fs)

    # Patch get_state_manager to return our instance
    with patch("swarm.api.routes.runs_control.get_state_manager", return_value=state_manager), \
         patch("swarm.api.routes.runs.get_state_manager", return_value=state_manager):

        # Also need to patch app state if used, but create_app initializes globals
        # We can pass repo_root to create_app, but it uses set_spec_manager internally

        # Let's patch where it's used in the route handler
        app = create_app(repo_root=mock_fs.parent.parent, enable_cors=False)
        client = TestClient(app)
        yield client

def test_stop_run_xss_in_reason(client, mock_fs):
    """Test that XSS payload in stop reason is sanitized in the report."""
    run_id = "test-run-xss"
    run_dir = mock_fs / run_id
    run_dir.mkdir()

    # Create initial run state
    state = {
        "run_id": run_id,
        "status": "running",
        "current_step": "step-1",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "context": {},
        "flow_id": "test-flow"
    }
    (run_dir / "run_state.json").write_text(json.dumps(state))

    # XSS Payload
    xss_payload = "<script>alert('xss')</script>"

    # Send stop request
    response = client.post(
        f"/api/runs/{run_id}/stop",
        json={"reason": xss_payload}
    )

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

    # Check the stop_report.md file
    report_path = run_dir / "stop_report.md"
    assert report_path.exists(), "stop_report.md was not created"

    content = report_path.read_text()

    # Verify XSS payload is NOT present in raw form
    assert xss_payload not in content, "XSS payload found in stop_report.md!"

    # Verify it IS present in sanitized form
    # html.escape converts < to &lt;, > to &gt;, etc.
    sanitized_payload = "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    # Note: ' might be escaped as &#x27; or kept as ' depending on python version/library used (html.escape handles quotes if quote=True)
    # Let's check for basic tags escaping first
    assert "&lt;script&gt;" in content
    assert "&lt;/script&gt;" in content
