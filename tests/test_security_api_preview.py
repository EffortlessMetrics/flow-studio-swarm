import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from swarm.tools.flow_studio.app import create_app
from swarm.tools.flow_studio.state import FlowStudioState
from swarm.flowstudio.schema import CompilePreviewRequest

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def mock_state(tmp_path):
    state = MagicMock(spec=FlowStudioState)
    state.repo_root = tmp_path
    state.core = MagicMock()
    state.run_inspector = MagicMock()
    state.run_service = MagicMock()
    return state

def test_api_station_compile_preview_path_traversal(client, mock_state):
    # Mock the dependency override
    app = client.app
    app.dependency_overrides[("swarm.tools.flow_studio.deps", "get_state")] = lambda: mock_state

    # Construct a request with path traversal in run_id
    payload = {
        "flow_id": "test-flow",
        "step_id": "test-step",
        "station_id": "test-station",
        "run_id": "../../../etc/passwd"
    }

    # We expect the API to return 400 Bad Request because of validation
    with patch("swarm.spec.compiler.SpecCompiler") as MockCompiler:
        mock_compiler_instance = MockCompiler.return_value

        response = client.post("/api/station/compile-preview", json=payload)

        # Verify it was rejected
        assert response.status_code == 400
        assert "invalid characters" in response.json()["error"] or "traversal sequence" in response.json()["error"]

        # Verify compiler was NOT called
        assert not mock_compiler_instance.compile.called

def test_api_station_compile_preview_valid_input(client, mock_state):
    # Mock the dependency override
    app = client.app
    app.dependency_overrides[("swarm.tools.flow_studio.deps", "get_state")] = lambda: mock_state

    # Construct a valid request
    payload = {
        "flow_id": "test-flow",
        "step_id": "test-step",
        "station_id": "test-station",
        "run_id": "valid-run-id"
    }

    with patch("swarm.spec.compiler.SpecCompiler") as MockCompiler:
        mock_compiler_instance = MockCompiler.return_value
        # Mock compile to return a mock plan object with required attributes
        mock_plan = MagicMock()
        mock_plan.flow_id = "test-flow"
        mock_plan.step_id = "test-step"
        mock_plan.station_id = "test-station"
        mock_plan.system_append = "sys"
        mock_plan.user_prompt = "user"
        mock_plan.model = "claude-3-opus-20240229"
        mock_plan.allowed_tools = []
        mock_plan.permission_mode = "default"
        mock_plan.max_turns = 10
        mock_plan.sandbox_enabled = False
        mock_plan.cwd = "/tmp"
        mock_plan.verification.required_artifacts = []
        mock_plan.verification.verification_commands = []
        mock_plan.prompt_hash = "hash"
        mock_plan.prompt_hash_v2 = "hash2"
        mock_plan.compiled_at = "2024-01-01T00:00:00Z"
        mock_plan.station_version = 1
        mock_plan.flow_version = 1

        mock_compiler_instance.compile.return_value = mock_plan

        response = client.post("/api/station/compile-preview", json=payload)

        # Verify success
        assert response.status_code == 200
        assert response.json()["flow_id"] == "test-flow"

        # Verify compiler was called
        assert mock_compiler_instance.compile.called
