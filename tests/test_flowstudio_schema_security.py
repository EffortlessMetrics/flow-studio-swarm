
import pytest
from pydantic import ValidationError
from swarm.flowstudio.schema import CompilePreviewRequest

def test_compile_preview_ids_valid():
    """Test valid IDs in CompilePreviewRequest."""
    req = CompilePreviewRequest(
        flow_id="test-flow",
        step_id="1.2.3",
        station_id="test-station",
        run_id="run-123"
    )
    assert req.flow_id == "test-flow"
    assert req.step_id == "1.2.3"
    assert req.station_id == "test-station"
    assert req.run_id == "run-123"

def test_compile_preview_ids_traversal():
    """Test IDs with traversal sequences."""
    # Test flow_id traversal
    with pytest.raises(ValidationError) as excinfo:
        CompilePreviewRequest(
            flow_id="../flow",
            step_id="step",
            station_id="station",
            run_id="run"
        )
    assert "traversal sequence" in str(excinfo.value) or "invalid characters" in str(excinfo.value)

    # Test run_id traversal
    with pytest.raises(ValidationError) as excinfo:
        CompilePreviewRequest(
            flow_id="flow",
            step_id="step",
            station_id="station",
            run_id="../run"
        )
    assert "traversal sequence" in str(excinfo.value) or "invalid characters" in str(excinfo.value)

def test_compile_preview_ids_invalid_chars():
    """Test IDs with invalid characters."""
    with pytest.raises(ValidationError) as excinfo:
        CompilePreviewRequest(
            flow_id="flow$1",
            step_id="step",
            station_id="station"
        )
    assert "invalid characters" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        CompilePreviewRequest(
            flow_id="flow",
            step_id="step",
            station_id="station",
            run_id="run/1" # Slash is not allowed in component
        )
    assert "contains invalid characters" in str(excinfo.value)
