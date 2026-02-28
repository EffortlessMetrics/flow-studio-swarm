import pytest
from fastapi import HTTPException
from swarm.api.routes.wisdom import get_wisdom_artifacts, get_wisdom_content, apply_wisdom_patch, reject_wisdom_patch, apply_wisdom_patches
from swarm.api.routes.evolution import get_run_evolution_patches, get_evolution_patch_details, validate_evolution_patch_endpoint, apply_evolution_patch_endpoint, reject_evolution_patch_endpoint
from swarm.api.services.spec_manager import set_spec_manager, SpecManager
import asyncio
from pathlib import Path

# Provide a mock SpecManager
set_spec_manager(SpecManager(repo_root=Path("/app")))

def test_wisdom_traversal_run_id():
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(get_wisdom_artifacts("foo/bar"))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_wisdom_traversal_artifact_name():
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(get_wisdom_content("123", "foo/bar", None))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_wisdom_traversal_apply_patch():
    from swarm.api.routes.wisdom import ApplyPatchRequest
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(apply_wisdom_patch("foo/bar", ApplyPatchRequest(artifact_name="valid", dry_run=True)))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_wisdom_traversal_reject_patch():
    from swarm.api.routes.wisdom import RejectPatchRequest
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(reject_wisdom_patch("foo/bar", RejectPatchRequest(artifact_name="valid", reason="test")))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_wisdom_traversal_apply_patches():
    from swarm.api.routes.wisdom import WisdomApplyRequest
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(apply_wisdom_patches("foo/bar", WisdomApplyRequest(patch_type="flow_evolution", policy="safe", dry_run=True)))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_evolution_traversal_run_id():
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(get_run_evolution_patches("foo/bar"))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_evolution_traversal_patch_id():
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(get_evolution_patch_details("123", "foo/bar"))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_evolution_traversal_validate():
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(validate_evolution_patch_endpoint("123", "foo/bar"))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_evolution_traversal_apply():
    from swarm.api.routes.evolution import ApplyEvolutionRequest
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(apply_evolution_patch_endpoint(ApplyEvolutionRequest(patch_id="foo/bar", dry_run=True, create_backup=True)))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(apply_evolution_patch_endpoint(ApplyEvolutionRequest(patch_id="foo/bar:valid", dry_run=True, create_backup=True)))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)

def test_evolution_traversal_reject():
    from swarm.api.routes.evolution import RejectEvolutionRequest
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(reject_evolution_patch_endpoint("123", "foo/bar", RejectEvolutionRequest(patch_id="foo/bar", reason="test")))
    assert excinfo.value.status_code == 400
    assert "invalid_path_parameter" in str(excinfo.value.detail)
