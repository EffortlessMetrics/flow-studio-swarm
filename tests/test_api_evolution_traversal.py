from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from swarm.api.routes import evolution


@pytest.mark.anyio
async def test_evolution_path_traversal():
    """Test that evolution endpoints validate run_id against path traversal."""

    # Mock runs root
    runs_root = Path("/tmp/runs")

    with patch("swarm.api.routes.evolution._get_runs_root", return_value=runs_root):

        # Test get_run_evolution_patches
        try:
            await evolution.get_run_evolution_patches(run_id="../etc")
            pytest.fail("Should have raised ValueError for traversal in get_run_evolution_patches")
        except ValueError as e:
            assert "run_id" in str(e) or "traversal sequence" in str(e)
        except HTTPException:
            # This is what happens when it's vulnerable (it tries to access the path and fails with 404)
            pytest.fail("Vulnerable: Traversal allowed in get_run_evolution_patches (got 404 instead of ValueError)")

        # Test get_evolution_patch_details
        try:
            await evolution.get_evolution_patch_details(run_id="../etc", patch_id="patch")
            pytest.fail("Should have raised ValueError for traversal in get_evolution_patch_details")
        except ValueError as e:
            assert "run_id" in str(e) or "traversal sequence" in str(e)
        except HTTPException:
            pytest.fail("Vulnerable: Traversal allowed in get_evolution_patch_details")

        # Test validate_evolution_patch_endpoint
        try:
            await evolution.validate_evolution_patch_endpoint(run_id="../etc", patch_id="patch")
            pytest.fail("Should have raised ValueError for traversal in validate_evolution_patch_endpoint")
        except ValueError as e:
            assert "run_id" in str(e) or "traversal sequence" in str(e)
        except HTTPException:
            pytest.fail("Vulnerable: Traversal allowed in validate_evolution_patch_endpoint")

        # Test reject_evolution_patch_endpoint
        try:
            await evolution.reject_evolution_patch_endpoint(
                run_id="../etc",
                patch_id="patch",
                request=MagicMock(reason="reason")
            )
            pytest.fail("Should have raised ValueError for traversal in reject_evolution_patch_endpoint")
        except ValueError as e:
            assert "run_id" in str(e) or "traversal sequence" in str(e)
        except HTTPException:
             pytest.fail("Vulnerable: Traversal allowed in reject_evolution_patch_endpoint")
