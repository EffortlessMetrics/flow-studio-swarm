import pytest
from pydantic import ValidationError

from swarm.api.routes.compile import CompilePreviewRequest


def test_compile_preview_request_valid_paths():
    """Test that valid relative paths and components are accepted."""
    request = CompilePreviewRequest(
        station_id="test-station",
        step_id="test-step",
        objective="test objective",
        flow_key="build",
        run_base="swarm/runs/preview",
    )
    assert request.station_id == "test-station"
    assert request.step_id == "test-step"
    assert request.flow_key == "build"
    assert request.run_base == "swarm/runs/preview"


def test_compile_preview_request_run_base_traversal():
    """Test that run_base rejects traversal sequences."""
    with pytest.raises(ValidationError, match="cannot contain traversal sequence"):
        CompilePreviewRequest(
            station_id="test-station",
            step_id="test-step",
            objective="test objective",
            run_base="../../etc/passwd",
        )


def test_compile_preview_request_run_base_absolute():
    """Test that run_base rejects absolute paths."""
    with pytest.raises(ValidationError, match="cannot be an absolute path"):
        CompilePreviewRequest(
            station_id="test-station",
            step_id="test-step",
            objective="test objective",
            run_base="/etc/passwd",
        )


def test_compile_preview_request_station_id_traversal():
    """Test that station_id rejects invalid characters/traversal."""
    with pytest.raises(ValidationError, match="invalid characters"):
        CompilePreviewRequest(
            station_id="../test",
            step_id="test-step",
            objective="test objective",
            run_base="swarm/runs/preview",
        )


def test_compile_preview_request_flow_key_traversal():
    """Test that flow_key rejects invalid characters/traversal."""
    with pytest.raises(ValidationError, match="invalid characters"):
        CompilePreviewRequest(
            station_id="test-station",
            step_id="test-step",
            objective="test objective",
            flow_key="../build",
            run_base="swarm/runs/preview",
        )


def test_compile_preview_request_step_id_traversal():
    """Test that step_id rejects invalid characters/traversal."""
    with pytest.raises(ValidationError, match="invalid characters"):
        CompilePreviewRequest(
            station_id="test-station",
            step_id="../step",
            objective="test objective",
            flow_key="build",
            run_base="swarm/runs/preview",
        )
