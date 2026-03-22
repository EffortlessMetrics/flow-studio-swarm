from unittest.mock import MagicMock

import pytest
from swarm.runtime.boundary_enforcement import BoundaryScanner, ViolationType, WorkspaceState
from swarm.runtime.workspace import Workspace


@pytest.fixture
def mock_workspace(tmp_path):
    workspace = MagicMock(spec=Workspace)
    workspace.root.return_value = tmp_path
    workspace.is_shadow.return_value = False
    return workspace


def test_detects_secret_in_file_content(mock_workspace, tmp_path):
    """Test that BoundaryScanner detects secrets in file content."""
    # Setup: Create a file with a secret in content
    # Using a filename that doesn't trigger the filename-based check
    secret_file = tmp_path / "my_script.py"
    secret_file.write_text('api_client = Client(api_key="sk-ant-test-key-12345")')

    # State with the changed file
    state = WorkspaceState(timestamp="2024-01-01T00:00:00Z", changed_files={"my_script.py"})

    scanner = BoundaryScanner(
        workspace=mock_workspace, step_id="step-1", repo_root=tmp_path, baseline_state=None
    )

    violations = scanner.scan(current_state=state)

    # Assert: Should find a SECRET_EXPOSURE violation
    secret_violations = [v for v in violations if v.type == ViolationType.SECRET_EXPOSURE]

    assert len(secret_violations) > 0, "Should detect secret in file content"
    assert "sk-ant-" in secret_violations[0].detail
    assert "Anthropic API Key" in secret_violations[0].detail


def test_skips_binary_files(mock_workspace, tmp_path):
    """Test that BoundaryScanner skips binary files even if they contain pattern."""
    # Create a binary file (invalid utf-8) that happens to have the bytes for a key
    binary_file = tmp_path / "data.bin"
    # 0xFF is invalid in UTF-8
    content = b"some binary data \xff " + b"sk-ant-test-key"
    binary_file.write_bytes(content)

    state = WorkspaceState(timestamp="2024-01-01T00:00:00Z", changed_files={"data.bin"})

    scanner = BoundaryScanner(
        workspace=mock_workspace, step_id="step-1", repo_root=tmp_path, baseline_state=None
    )

    violations = scanner.scan(current_state=state)

    # Assert: Should NOT find violation (UnicodeDecodeError caught)
    secret_violations = [v for v in violations if v.type == ViolationType.SECRET_EXPOSURE]
    assert len(secret_violations) == 0


def test_skips_large_files(mock_workspace, tmp_path):
    """Test that BoundaryScanner skips files larger than limit."""
    large_file = tmp_path / "large.txt"
    # Create 1.1MB file
    large_file.write_text("a" * (1024 * 1024 + 100) + "sk-ant-test-key")

    state = WorkspaceState(timestamp="2024-01-01T00:00:00Z", changed_files={"large.txt"})

    scanner = BoundaryScanner(
        workspace=mock_workspace, step_id="step-1", repo_root=tmp_path, baseline_state=None
    )

    violations = scanner.scan(current_state=state)

    # Assert: Should NOT find violation (size limit)
    secret_violations = [v for v in violations if v.type == ViolationType.SECRET_EXPOSURE]
    assert len(secret_violations) == 0
