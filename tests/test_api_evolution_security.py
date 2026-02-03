
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from pathlib import Path
from fastapi import HTTPException
from swarm.api.routes.evolution import (
    get_run_evolution_patches,
    get_evolution_patch_details,
    validate_evolution_patch_endpoint,
    apply_evolution_patch_endpoint,
    reject_evolution_patch_endpoint,
    ApplyEvolutionRequest,
    RejectEvolutionRequest,
)

def run_async(coro):
    return asyncio.run(coro)

# Mock paths
mock_runs_root = Path("/tmp/mock_runs")
mock_repo_root = Path("/tmp/mock_repo")

def test_get_run_evolution_patches_traversal():
    """Test that path traversal in run_id is rejected."""
    async def _test():
        with pytest.raises(HTTPException) as excinfo:
            await get_run_evolution_patches(run_id="../etc/passwd")

        assert excinfo.value.status_code == 400
        assert "invalid characters" in str(excinfo.value.detail) or "traversal sequence" in str(excinfo.value.detail)

    run_async(_test())

def test_get_evolution_patch_details_traversal_run_id():
    """Test that path traversal in run_id is rejected."""
    async def _test():
        with pytest.raises(HTTPException) as excinfo:
            await get_evolution_patch_details(run_id="../etc/passwd", patch_id="PATCH-001")

        assert excinfo.value.status_code == 400

    run_async(_test())

def test_get_evolution_patch_details_traversal_patch_id():
    """Test that path traversal in patch_id is rejected."""
    async def _test():
        with pytest.raises(HTTPException) as excinfo:
            await get_evolution_patch_details(run_id="run-123", patch_id="../etc/passwd")

        assert excinfo.value.status_code == 400

    run_async(_test())

def test_validate_evolution_patch_endpoint_traversal_run_id():
    """Test that path traversal in run_id is rejected."""
    async def _test():
        with pytest.raises(HTTPException) as excinfo:
            await validate_evolution_patch_endpoint(run_id="../etc/passwd", patch_id="PATCH-001")

        assert excinfo.value.status_code == 400

    run_async(_test())

def test_validate_evolution_patch_endpoint_traversal_patch_id():
    """Test that path traversal in patch_id is rejected."""
    async def _test():
        with pytest.raises(HTTPException) as excinfo:
            await validate_evolution_patch_endpoint(run_id="run-123", patch_id="../etc/passwd")

        assert excinfo.value.status_code == 400

    run_async(_test())

def test_apply_evolution_patch_endpoint_traversal_split():
    """Test that path traversal in run_id:patch_id is rejected."""
    async def _test():
        request = ApplyEvolutionRequest(patch_id="../etc/passwd:PATCH-001")

        # We need to mock _get_runs_root/repo_root because they are called before validation in this endpoint
        with patch("swarm.api.routes.evolution._get_runs_root", return_value=mock_runs_root), \
             patch("swarm.api.routes.evolution._get_repo_root", return_value=mock_repo_root), \
             patch("swarm.api.routes.evolution._get_evolution_module") as mock_module:

            mock_module.return_value = {
                "list_pending_patches": MagicMock(return_value=[])
            }

            with pytest.raises(HTTPException) as excinfo:
                await apply_evolution_patch_endpoint(request)

            assert excinfo.value.status_code == 400

    run_async(_test())

def test_apply_evolution_patch_endpoint_traversal_patch_id():
    """Test that path traversal in patch_id is rejected."""
    async def _test():
        request = ApplyEvolutionRequest(patch_id="../etc/passwd")

        with patch("swarm.api.routes.evolution._get_runs_root", return_value=mock_runs_root), \
             patch("swarm.api.routes.evolution._get_repo_root", return_value=mock_repo_root), \
             patch("swarm.api.routes.evolution._get_evolution_module") as mock_module:

            mock_module.return_value = {
                "list_pending_patches": MagicMock(return_value=[])
            }

            with pytest.raises(HTTPException) as excinfo:
                await apply_evolution_patch_endpoint(request)

            assert excinfo.value.status_code == 400

    run_async(_test())

def test_reject_evolution_patch_endpoint_traversal_run_id():
    """Test that path traversal in run_id is rejected."""
    async def _test():
        request = RejectEvolutionRequest(patch_id="PATCH-001", reason="bad")

        with pytest.raises(HTTPException) as excinfo:
            await reject_evolution_patch_endpoint(run_id="../etc/passwd", patch_id="PATCH-001", request=request)

        assert excinfo.value.status_code == 400

    run_async(_test())

def test_reject_evolution_patch_endpoint_traversal_patch_id():
    """Test that path traversal in patch_id is rejected."""
    async def _test():
        request = RejectEvolutionRequest(patch_id="../etc/passwd", reason="bad")

        with pytest.raises(HTTPException) as excinfo:
            await reject_evolution_patch_endpoint(run_id="run-123", patch_id="../etc/passwd", request=request)

        assert excinfo.value.status_code == 400

    run_async(_test())
