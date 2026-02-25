
import pytest
from swarm.api.routes.compile import CompilePreviewRequest
from pydantic import ValidationError

def test_compile_preview_request_traversal_fails():
    """Verify that CompilePreviewRequest rejects path traversal in run_base."""
    with pytest.raises(ValidationError, match="run_base cannot contain traversal sequence"):
        CompilePreviewRequest(
            station_id="test",
            step_id="test",
            objective="test",
            run_base="../../../etc/passwd"
        )

def test_compile_preview_request_absolute_path_fails():
    """Verify that CompilePreviewRequest rejects absolute paths in run_base."""
    with pytest.raises(ValidationError, match="run_base must be a relative path"):
        CompilePreviewRequest(
            station_id="test",
            step_id="test",
            objective="test",
            run_base="/etc/passwd"
        )
