
import pytest
from pydantic import ValidationError
from swarm.api.routes.compile import CompilePreviewRequest

def test_compile_preview_run_base_valid():
    """Test valid run_base paths."""
    valid_paths = [
        "swarm/runs/preview",
        "runs/test-run",
        "temp/preview",
        "my_run",
        "run-123.preview"
    ]
    for path in valid_paths:
        req = CompilePreviewRequest(
            station_id="test",
            step_id="test",
            objective="test",
            run_base=path
        )
        assert req.run_base == path

def test_compile_preview_run_base_traversal():
    """Test run_base paths with traversal sequences."""
    invalid_paths = [
        "../etc/passwd",
        "runs/../../etc",
        "..",
        "runs/..",
        "/etc/passwd/.."
    ]
    for path in invalid_paths:
        with pytest.raises(ValidationError) as excinfo:
            CompilePreviewRequest(
                station_id="test",
                step_id="test",
                objective="test",
                run_base=path
            )
        assert "traversal sequence" in str(excinfo.value) or "relative path" in str(excinfo.value)

def test_compile_preview_run_base_absolute():
    """Test absolute run_base paths."""
    invalid_paths = [
        "/etc/passwd",
        "/tmp/run",
        "/",
    ]
    for path in invalid_paths:
        with pytest.raises(ValidationError) as excinfo:
            CompilePreviewRequest(
                station_id="test",
                step_id="test",
                objective="test",
                run_base=path
            )
        assert "relative path" in str(excinfo.value)

def test_compile_preview_run_base_invalid_chars():
    """Test run_base paths with invalid characters."""
    invalid_paths = [
        "runs/test$run",
        "runs/test run",
        "runs/test*run",
        "runs/test;run"
    ]
    for path in invalid_paths:
        with pytest.raises(ValidationError) as excinfo:
            CompilePreviewRequest(
                station_id="test",
                step_id="test",
                objective="test",
                run_base=path
            )
        assert "invalid characters" in str(excinfo.value)
