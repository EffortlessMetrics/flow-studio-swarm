import pytest
from pydantic import ValidationError
from swarm.api.routes.compile import CompilePreviewRequest

def test_compile_preview_valid_path():
    """Test that a valid relative path is accepted."""
    req = CompilePreviewRequest(
        station_id="test",
        step_id="test",
        objective="test",
        run_base="swarm/runs/preview"
    )
    assert req.run_base == "swarm/runs/preview"

def test_compile_preview_rejects_traversal():
    """Test that path traversal sequences are rejected."""
    with pytest.raises(ValidationError) as excinfo:
        CompilePreviewRequest(
            station_id="test",
            step_id="test",
            objective="test",
            run_base="../../../etc/passwd"
        )
    assert "run_base cannot contain path traversal '..'" in str(excinfo.value)

def test_compile_preview_rejects_absolute_path():
    """Test that absolute paths are rejected."""
    with pytest.raises(ValidationError) as excinfo:
        CompilePreviewRequest(
            station_id="test",
            step_id="test",
            objective="test",
            run_base="/etc/passwd"
        )
    assert "run_base must be a relative path" in str(excinfo.value)
