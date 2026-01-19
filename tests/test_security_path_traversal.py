
import pytest
from swarm.tools.flow_studio.services.run_artifacts import (
    RunArtifactsError,
    load_transcript,
    load_receipt,
    resolve_run_path,
)

def test_resolve_run_path_traversal():
    """Test that path traversal attempts in run_id are rejected."""
    with pytest.raises(RunArtifactsError) as excinfo:
        resolve_run_path("../etc/passwd", None)

    assert excinfo.value.status_code == 400
    assert "contains invalid characters" in str(excinfo.value.payload)

def test_load_transcript_traversal():
    """Test that path traversal attempts in flow_key and step_id are rejected."""
    # Mock resolve_run_path to avoid filesystem checks for this test if possible,
    # but since validation happens before, it should trigger first.

    # Test invalid flow_key
    with pytest.raises(RunArtifactsError) as excinfo:
        load_transcript("valid_run", "../bad_flow", "step1", None)

    assert excinfo.value.status_code == 400
    assert "flow_key contains invalid characters" in str(excinfo.value.payload)

    # Test invalid step_id
    with pytest.raises(RunArtifactsError) as excinfo:
        load_transcript("valid_run", "valid_flow", "../bad_step", None)

    assert excinfo.value.status_code == 400
    assert "step_id contains invalid characters" in str(excinfo.value.payload)

def test_load_receipt_traversal():
    """Test that path traversal attempts in flow_key and step_id are rejected."""

    # Test invalid flow_key
    with pytest.raises(RunArtifactsError) as excinfo:
        load_receipt("valid_run", "../bad_flow", "step1", None)

    assert excinfo.value.status_code == 400
    assert "flow_key contains invalid characters" in str(excinfo.value.payload)

    # Test invalid step_id
    with pytest.raises(RunArtifactsError) as excinfo:
        load_receipt("valid_run", "valid_flow", "../bad_step", None)

    assert excinfo.value.status_code == 400
    assert "step_id contains invalid characters" in str(excinfo.value.payload)

def test_valid_inputs_pass_validation():
    """Test that valid inputs pass validation (though they might fail later if files don't exist)."""

    # Validation should pass, but resolve_run_path will fail finding the run if it doesn't exist.
    # We expect 404 (Run not found) instead of 400 (Validation error).

    with pytest.raises(RunArtifactsError) as excinfo:
        resolve_run_path("valid-run-id", None)

    # If it failed validation, it would be 400.
    # Since it passed validation but failed to find run, it should be 404.
    assert excinfo.value.status_code == 404
    assert "Run 'valid-run-id' not found" in str(excinfo.value.payload)
