
import asyncio
import pytest
from fastapi import HTTPException, Request
from pathlib import Path
from swarm.api.server import set_spec_manager
from swarm.api.services.spec_manager import clear_spec_manager

# Mock SpecManager
class MockSpecManager:
    def __init__(self, runs_root):
        self.runs_root = runs_root
        self.repo_root = runs_root.parent

@pytest.fixture
def mock_app_context(tmp_path):
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    clear_spec_manager()
    set_spec_manager(MockSpecManager(runs_root))

    yield

    clear_spec_manager()

def run_async(coro):
    return asyncio.run(coro)

def test_events_stream_traversal(mock_app_context):
    from swarm.api.routes.events import stream_run_events

    async def run_test():
        request = Request({"type": "http"})
        try:
            await stream_run_events("../bad_run", request)
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400
            assert "invalid_request" in str(e.detail)

    run_async(run_test())

def test_events_write_traversal(mock_app_context):
    from swarm.api.routes.events import write_event, write_event_sync
    from swarm.api.server import get_spec_manager

    runs_root = get_spec_manager().runs_root

    # Test write_event (async)
    async def run_test():
        try:
            await write_event("../bad_run", runs_root, "test", {})
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            assert "traversal sequence" in str(e) or "invalid characters" in str(e)

    run_async(run_test())

    # Test write_event_sync
    try:
        write_event_sync("../bad_run", runs_root, "test", {})
        pytest.fail("Should have raised ValueError")
    except ValueError as e:
        assert "traversal sequence" in str(e) or "invalid characters" in str(e)

def test_wisdom_artifacts_traversal(mock_app_context):
    from swarm.api.routes.wisdom import get_wisdom_artifacts

    async def run_test():
        try:
            await get_wisdom_artifacts("../bad_run")
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400
            assert "invalid_request" in str(e.detail)

    run_async(run_test())

def test_wisdom_content_traversal(mock_app_context):
    from swarm.api.routes.wisdom import get_wisdom_content

    async def run_test():
        # Test bad run_id
        try:
            await get_wisdom_content("../bad_run", "artifact.md")
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400

        # Test bad artifact_name
        try:
            await get_wisdom_content("valid_run", "../bad_artifact")
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400

    run_async(run_test())

def test_wisdom_apply_patch_traversal(mock_app_context):
    from swarm.api.routes.wisdom import apply_wisdom_patch, ApplyPatchRequest

    async def run_test():
        request = ApplyPatchRequest(artifact_name="patch.json")

        # Test bad run_id
        try:
            await apply_wisdom_patch("../bad_run", request)
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400

        # Test bad artifact_name in request
        request_bad = ApplyPatchRequest(artifact_name="../bad_patch.json")
        try:
            await apply_wisdom_patch("valid_run", request_bad)
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400

    run_async(run_test())

def test_wisdom_reject_patch_traversal(mock_app_context):
    from swarm.api.routes.wisdom import reject_wisdom_patch, RejectPatchRequest

    async def run_test():
        request = RejectPatchRequest(reason="bad")

        # Test bad run_id
        try:
            await reject_wisdom_patch("../bad_run", request)
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400

        # Test bad artifact_name in request
        request_bad = RejectPatchRequest(artifact_name="../bad_patch.json", reason="bad")
        try:
            await reject_wisdom_patch("valid_run", request_bad)
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400

    run_async(run_test())

def test_wisdom_apply_patches_traversal(mock_app_context):
    from swarm.api.routes.wisdom import apply_wisdom_patches, WisdomApplyRequest

    async def run_test():
        request = WisdomApplyRequest()
        try:
            await apply_wisdom_patches("../bad_run", request)
            pytest.fail("Should have raised HTTPException(400)")
        except HTTPException as e:
            assert e.status_code == 400

    run_async(run_test())
