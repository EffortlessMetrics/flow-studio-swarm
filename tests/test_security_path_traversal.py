import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from swarm.tools.flow_studio.services.run_artifacts import load_transcript, load_receipt
from swarm.tools.flow_studio.state import FlowStudioState

# We expect these tests to fail initially because the validation is missing.
# After the fix, they should pass.

def test_load_transcript_validates_run_id():
    """Test that load_transcript raises ValueError for invalid run_id."""
    run_id = "../../etc/passwd"
    flow_key = "valid_flow"
    step_id = "valid_step"

    with pytest.raises(ValueError, match="Invalid run_id"):
        load_transcript(run_id, flow_key, step_id, None)

def test_load_transcript_validates_flow_key():
    """Test that load_transcript raises ValueError for invalid flow_key."""
    run_id = "valid_run"
    flow_key = "../invalid_flow"
    step_id = "valid_step"

    # We mock resolve_run_path to bypass run_id check (if it was checked there) or file existence checks
    with patch("swarm.tools.flow_studio.services.run_artifacts.resolve_run_path") as mock_resolve:
        mock_resolve.return_value = Path("/tmp/runs/valid_run")

        with pytest.raises(ValueError, match="Invalid flow_key"):
            load_transcript(run_id, flow_key, step_id, None)

def test_load_transcript_validates_step_id():
    """Test that load_transcript raises ValueError for invalid step_id."""
    run_id = "valid_run"
    flow_key = "valid_flow"
    step_id = "../invalid_step"

    with patch("swarm.tools.flow_studio.services.run_artifacts.resolve_run_path") as mock_resolve:
        mock_resolve.return_value = Path("/tmp/runs/valid_run")

        with pytest.raises(ValueError, match="Invalid step_id"):
            load_transcript(run_id, flow_key, step_id, None)

def test_load_receipt_validates_inputs():
    """Test that load_receipt validates inputs."""
    run_id = "valid_run"
    flow_key = "valid_flow"
    step_id = "valid_step; rm -rf /" # malicious input

    with patch("swarm.tools.flow_studio.services.run_artifacts.resolve_run_path") as mock_resolve:
        mock_resolve.return_value = Path("/tmp/runs/valid_run")

        with pytest.raises(ValueError, match="Invalid step_id"):
            load_receipt(run_id, flow_key, step_id, None)
