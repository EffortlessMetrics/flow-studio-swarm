import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from swarm.api.routes.db import rebuild_database, ingest_run_events, DBRebuildRequest
from swarm.api.routes.evolution import (
    reject_evolution_patch_endpoint,
    RejectEvolutionRequest,
    apply_evolution_patch_endpoint,
    ApplyEvolutionRequest
)

def test_db_rebuild_path_traversal_blocked():
    """Test that rebuild_database BLOCKS path traversal (after fix)."""
    async def run_test():
        with patch("swarm.runtime.resilient_db.get_resilient_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_db.health.healthy = True
            mock_db.health.needs_rebuild = False

            req = DBRebuildRequest(run_ids=["../etc/passwd"], force=True)

            response = await rebuild_database(req)

            # Verify it did NOT call the DB with the traversal path
            mock_db.rebuild_from_events_safe.assert_not_called()

            # Verify it reported an error in the response
            assert len(response.errors) == 1
            assert response.errors[0]["run_id"] == "../etc/passwd"
            assert "invalid characters" in response.errors[0]["error"] or "traversal sequence" in response.errors[0]["error"]

    asyncio.run(run_test())

def test_evolution_reject_path_traversal_blocked():
    """Test that reject_evolution_patch_endpoint BLOCKS path traversal (after fix)."""
    async def run_test():
        with patch("swarm.api.routes.evolution._get_runs_root") as mock_root_func:
            mock_root_path = MagicMock()
            mock_root_func.return_value = mock_root_path

            mock_wisdom_dir = MagicMock()
            mock_root_path.__truediv__.return_value.__truediv__.return_value = mock_wisdom_dir
            mock_wisdom_dir.exists.return_value = True

            mock_rejection_path = MagicMock()
            mock_wisdom_dir.__truediv__.return_value = mock_rejection_path

            # We expect HTTPException(400)
            with pytest.raises(HTTPException) as exc_info:
                await reject_evolution_patch_endpoint(
                    run_id="valid_run",
                    patch_id="../bad_patch",
                    request=RejectEvolutionRequest(patch_id="../bad_patch", reason="test")
                )

            assert exc_info.value.status_code == 400
            assert "invalid characters" in str(exc_info.value.detail) or "traversal sequence" in str(exc_info.value.detail)

            # Verify write_text was NOT called
            mock_rejection_path.write_text.assert_not_called()

    asyncio.run(run_test())

def test_evolution_apply_path_traversal_blocked():
    """Test that apply_evolution_patch_endpoint BLOCKS path traversal."""
    async def run_test():
        # Test combined run_id:patch_id
        with pytest.raises(HTTPException) as exc_info:
            await apply_evolution_patch_endpoint(
                request=ApplyEvolutionRequest(patch_id="../bad_run:patch_001")
            )
        assert exc_info.value.status_code == 400

        with pytest.raises(HTTPException) as exc_info:
            await apply_evolution_patch_endpoint(
                request=ApplyEvolutionRequest(patch_id="run_001:../bad_patch")
            )
        assert exc_info.value.status_code == 400

        # Test patch_id only (requires lookup)
        # We need to mock list_pending_patches or it will fail on lookup
        # But validation should happen BEFORE lookup for patch_id

        with pytest.raises(HTTPException) as exc_info:
            await apply_evolution_patch_endpoint(
                request=ApplyEvolutionRequest(patch_id="../bad_patch_lookup")
            )
        assert exc_info.value.status_code == 400

    asyncio.run(run_test())
