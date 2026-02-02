
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, Request

from swarm.api.routes.db import ingest_run_events, rebuild_database, DBRebuildRequest
from swarm.api.routes.events import stream_run_events
from swarm.api.routes.evolution import (
    get_run_evolution_patches,
    get_evolution_patch_details,
    validate_evolution_patch_endpoint,
    apply_evolution_patch_endpoint,
    reject_evolution_patch_endpoint,
    ApplyEvolutionRequest,
    RejectEvolutionRequest
)
from swarm.api.routes.wisdom import (
    get_wisdom_artifacts,
    get_wisdom_content,
    apply_wisdom_patch,
    reject_wisdom_patch,
    apply_wisdom_patches,
    ApplyPatchRequest,
    RejectPatchRequest,
    WisdomApplyRequest
)

# Mock run_id with traversal
TRAVERSAL_ID = "../secrets"
TRAVERSAL_ARTIFACT = "../etc/passwd"

def async_test(coro):
    """Helper to run async tests."""
    return asyncio.run(coro)

@patch("swarm.runtime.resilient_db.get_resilient_db")
def test_db_ingest_run_events_traversal(mock_get_db):
    """Test ingest_run_events with traversal run_id."""
    with pytest.raises(HTTPException) as exc:
        async_test(ingest_run_events(TRAVERSAL_ID))
    assert exc.value.status_code == 400
    assert "invalid_run_id" in str(exc.value.detail) or "invalid characters" in str(exc.value.detail)

@patch("swarm.runtime.resilient_db.get_resilient_db")
def test_db_rebuild_database_traversal(mock_get_db):
    """Test rebuild_database with traversal run_ids."""
    req = DBRebuildRequest(run_ids=[TRAVERSAL_ID])
    with pytest.raises(HTTPException) as exc:
        async_test(rebuild_database(req))
    assert exc.value.status_code == 400
    assert "invalid_run_id" in str(exc.value.detail) or "invalid characters" in str(exc.value.detail)

@patch("swarm.api.server.get_spec_manager")
@patch("swarm.runtime.resilient_db.check_db_health")
def test_events_stream_traversal(mock_health, mock_get_spec):
    """Test stream_run_events with traversal run_id."""
    request = AsyncMock(spec=Request)
    request.is_disconnected.return_value = True

    # Mock runs_root
    mock_manager = MagicMock()
    mock_manager.runs_root.exists.return_value = True
    mock_get_spec.return_value = mock_manager

    with pytest.raises(HTTPException) as exc:
        async_test(stream_run_events(TRAVERSAL_ID, request))
    assert exc.value.status_code == 400

@patch("swarm.api.routes.evolution._get_evolution_module")
@patch("swarm.api.routes.evolution._get_runs_root")
def test_evolution_endpoints_traversal(mock_runs_root, mock_evolution):
    """Test evolution endpoints with traversal run_id."""
    mock_evolution.return_value = {
        "list_pending_patches": MagicMock(return_value=[]),
        "generate_evolution_patch": MagicMock(return_value=[])
    }
    mock_runs_root.return_value = MagicMock()

    # get_run_evolution_patches
    with pytest.raises(HTTPException) as exc:
        async_test(get_run_evolution_patches(TRAVERSAL_ID))
    assert exc.value.status_code == 400

    # get_evolution_patch_details
    with pytest.raises(HTTPException) as exc:
        async_test(get_evolution_patch_details(TRAVERSAL_ID, "patch1"))
    assert exc.value.status_code == 400

    # validate_evolution_patch_endpoint
    with pytest.raises(HTTPException) as exc:
        async_test(validate_evolution_patch_endpoint(TRAVERSAL_ID, "patch1"))
    assert exc.value.status_code == 400

    # reject_evolution_patch_endpoint - run_id traversal
    req = RejectEvolutionRequest(patch_id="patch1", reason="bad")
    with pytest.raises(HTTPException) as exc:
        async_test(reject_evolution_patch_endpoint(TRAVERSAL_ID, "patch1", req))
    assert exc.value.status_code == 400

    # reject_evolution_patch_endpoint - patch_id traversal
    req = RejectEvolutionRequest(patch_id=TRAVERSAL_ID, reason="bad")
    with pytest.raises(HTTPException) as exc:
        async_test(reject_evolution_patch_endpoint("valid-run", TRAVERSAL_ID, req))
    assert exc.value.status_code == 400

@patch("swarm.api.routes.evolution._get_evolution_module")
@patch("swarm.api.routes.evolution._get_runs_root")
@patch("swarm.api.routes.evolution._get_repo_root")
def test_evolution_apply_traversal(mock_repo, mock_runs, mock_evo):
    """Test apply_evolution_patch_endpoint with traversal."""
    # Test with run_id in patch_id
    req = ApplyEvolutionRequest(patch_id=f"{TRAVERSAL_ID}:patch1")
    with pytest.raises(HTTPException) as exc:
        async_test(apply_evolution_patch_endpoint(req))
    assert exc.value.status_code == 400

@patch("swarm.api.routes.wisdom._get_runs_root")
def test_wisdom_get_artifacts_traversal(mock_root):
    mock_root.return_value = MagicMock()
    with pytest.raises(HTTPException) as exc:
        async_test(get_wisdom_artifacts(TRAVERSAL_ID))
    assert exc.value.status_code == 400

@patch("swarm.api.routes.wisdom._get_runs_root")
def test_wisdom_get_content_traversal(mock_root):
    mock_root.return_value = MagicMock()
    # Test run_id traversal
    with pytest.raises(HTTPException) as exc:
        async_test(get_wisdom_content(TRAVERSAL_ID, "artifact.md"))
    assert exc.value.status_code == 400

    # Test artifact_name traversal
    # Assuming run_id is valid for this sub-test
    with pytest.raises(HTTPException) as exc:
        async_test(get_wisdom_content("valid-run", TRAVERSAL_ARTIFACT))
    assert exc.value.status_code == 400

@patch("swarm.api.routes.wisdom._get_runs_root")
def test_wisdom_apply_traversal(mock_root):
    mock_root.return_value = MagicMock()
    # apply_wisdom_patch
    req = ApplyPatchRequest(artifact_name="patch.md")
    with pytest.raises(HTTPException) as exc:
        async_test(apply_wisdom_patch(TRAVERSAL_ID, req))
    assert exc.value.status_code == 400

    # artifact traversal
    req = ApplyPatchRequest(artifact_name=TRAVERSAL_ARTIFACT)
    with pytest.raises(HTTPException) as exc:
        async_test(apply_wisdom_patch("valid-run", req))
    assert exc.value.status_code == 400

@patch("swarm.api.routes.wisdom._get_runs_root")
def test_wisdom_reject_traversal(mock_root):
    mock_root.return_value = MagicMock()
    req = RejectPatchRequest(artifact_name="patch.md", reason="bad")
    with pytest.raises(HTTPException) as exc:
        async_test(reject_wisdom_patch(TRAVERSAL_ID, req))
    assert exc.value.status_code == 400

@patch("swarm.api.routes.wisdom._get_repo_root")
@patch("swarm.api.routes.wisdom._get_runs_root")
def test_wisdom_apply_patches_traversal(mock_root, mock_repo):
    mock_root.return_value = MagicMock()
    req = WisdomApplyRequest()
    with pytest.raises(HTTPException) as exc:
        async_test(apply_wisdom_patches(TRAVERSAL_ID, req))
    assert exc.value.status_code == 400
