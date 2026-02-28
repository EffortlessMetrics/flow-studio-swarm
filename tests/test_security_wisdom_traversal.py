"""
Security regression tests for path traversal vulnerabilities in Wisdom and Evolution APIs.
"""

import sys
from pathlib import Path
import pytest
import asyncio

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from swarm.api.routes.wisdom import get_wisdom_artifacts, get_wisdom_content, apply_wisdom_patch, reject_wisdom_patch, apply_wisdom_patches
from swarm.api.routes.evolution import get_run_evolution_patches, get_evolution_patch_details, validate_evolution_patch_endpoint, apply_evolution_patch_endpoint, reject_evolution_patch_endpoint
from swarm.api.server import set_spec_manager
from swarm.api.services.spec_manager import SpecManager

def setup_module():
    manager = SpecManager(repo_root=Path("/tmp/repo"))
    set_spec_manager(manager)

def test_wisdom_path_traversal():
    """Test that path traversal sequences return 400 Bad Request in wisdom endpoints via route functions."""
    from fastapi import HTTPException

    # Test run_id traversal
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_wisdom_artifacts("..\\something"))
    assert exc_info.value.status_code == 400
    assert "invalid_path_parameter" in exc_info.value.detail["error"]

    # Test artifact_name traversal
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_wisdom_content("valid_run", "..\\something"))
    assert exc_info.value.status_code == 400
    assert "invalid_path_parameter" in exc_info.value.detail["error"]


def test_evolution_path_traversal():
    """Test that path traversal sequences return 400 Bad Request in evolution endpoints via route functions."""
    from fastapi import HTTPException
    from swarm.api.routes.evolution import ApplyEvolutionRequest

    # Test run_id traversal
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_run_evolution_patches("..\\something"))
    assert exc_info.value.status_code == 400
    assert "invalid_path_parameter" in exc_info.value.detail["error"]

    # Test patch_id traversal
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_evolution_patch_details("valid_run", "..\\something"))
    assert exc_info.value.status_code == 400
    assert "invalid_path_parameter" in exc_info.value.detail["error"]

    # Test apply patch payload traversal
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(apply_evolution_patch_endpoint(ApplyEvolutionRequest(patch_id="..\\something", dry_run=True, create_backup=False)))
    assert exc_info.value.status_code == 400
    assert "invalid_path_parameter" in exc_info.value.detail["error"]

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(apply_evolution_patch_endpoint(ApplyEvolutionRequest(patch_id="run_id:..\\something", dry_run=True, create_backup=False)))
    assert exc_info.value.status_code == 400
    assert "invalid_path_parameter" in exc_info.value.detail["error"]

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(apply_evolution_patch_endpoint(ApplyEvolutionRequest(patch_id="..\\something:patch_id", dry_run=True, create_backup=False)))
    assert exc_info.value.status_code == 400
    assert "invalid_path_parameter" in exc_info.value.detail["error"]
