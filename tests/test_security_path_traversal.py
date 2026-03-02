import pytest
from swarm.runtime import storage
from swarm.runtime.safe_paths import validate_path_component
from swarm.tools.flow_studio.services import run_artifacts
from swarm.tools.run_inspector import RunInspector
from fastapi.testclient import TestClient
from swarm.api.asgi import app

client = TestClient(app)


def test_validate_path_component_valid():
    """Test that valid path components pass validation."""
    assert validate_path_component("valid-id_123.json") == "valid-id_123.json"
    assert validate_path_component("run-20260119-143022-abc123") == "run-20260119-143022-abc123"
    assert validate_path_component("signal") == "signal"
    assert validate_path_component("step_1") == "step_1"


def test_validate_path_component_empty():
    """Test that empty strings are rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_path_component("")


def test_validate_path_component_traversal():
    """Test that traversal sequences are rejected."""
    with pytest.raises(ValueError, match="traversal sequence"):
        validate_path_component("..")

    with pytest.raises(ValueError, match="traversal sequence"):
        validate_path_component(".")


def test_validate_path_component_slashes():
    """Test that forward slashes are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
        validate_path_component("foo/bar")

    with pytest.raises(ValueError, match="invalid characters"):
        validate_path_component("../foo")


def test_validate_path_component_backslashes():
    """Test that backslashes are rejected (Windows path traversal)."""
    with pytest.raises(ValueError, match="invalid characters"):
        validate_path_component("foo\\bar")

    with pytest.raises(ValueError, match="invalid characters"):
        validate_path_component("..\\etc")


def test_storage_get_run_path_validation():
    with pytest.raises(ValueError, match="run_id"):
        storage.get_run_path("../etc")


def test_storage_find_run_path_validation():
    """Test that find_run_path validates run_id against path traversal."""
    with pytest.raises(ValueError, match="run_id"):
        storage.find_run_path("../etc")

    with pytest.raises(ValueError, match="run_id"):
        storage.find_run_path("..\\etc")

    with pytest.raises(ValueError, match="run_id"):
        storage.find_run_path("..")


def test_storage_get_run_type_validation():
    """Test that get_run_type validates run_id against path traversal."""
    with pytest.raises(ValueError, match="run_id"):
        storage.get_run_type("../etc")

    with pytest.raises(ValueError, match="run_id"):
        storage.get_run_type("..\\etc")

    with pytest.raises(ValueError, match="run_id"):
        storage.get_run_type("..")


def test_run_artifacts_validation():
    # Validation happens before any IO or inspector access

    with pytest.raises(ValueError, match="run_id"):
        run_artifacts.resolve_run_path("../etc", None)

    with pytest.raises(ValueError, match="flow_key"):
        run_artifacts.load_transcript("valid_run", "../bad_flow", "step", None)

    with pytest.raises(ValueError, match="step_id"):
        run_artifacts.load_transcript("valid_run", "valid_flow", "step/bad", None)

    with pytest.raises(ValueError, match="flow_key"):
        run_artifacts.load_receipt("valid_run", "../bad_flow", "step", None)

    with pytest.raises(ValueError, match="step_id"):
        run_artifacts.load_receipt("valid_run", "valid_flow", "step/bad", None)


def test_run_inspector_validation():
    """Test that RunInspector validates path components."""
    # RunInspector validates run_id in get_run_path
    inspector = RunInspector()

    with pytest.raises(ValueError, match="run_id"):
        inspector.get_run_path("../etc")

    with pytest.raises(ValueError, match="run_id"):
        inspector.get_run_path("..\\etc")

    # get_step_status validates flow_key
    with pytest.raises(ValueError, match="flow_key"):
        inspector.get_step_status("valid_run", "../bad", "step")

    # get_flow_status validates flow_key
    with pytest.raises(ValueError, match="flow_key"):
        inspector.get_flow_status("valid_run", "../bad")


def test_spec_manager_path_validation(tmp_path):
    """Test that SpecManager validates path components against traversal."""
    from swarm.api.services.spec_manager import SpecManager

    manager = SpecManager(repo_root=tmp_path)

    # get_flow validates flow_id
    with pytest.raises(ValueError, match="flow_id"):
        manager.get_flow("../etc/passwd")

    with pytest.raises(ValueError, match="flow_id"):
        manager.get_flow("..\\windows\\system32")

    with pytest.raises(ValueError, match="flow_id"):
        manager.get_flow("..")

    # get_template validates template_id
    with pytest.raises(ValueError, match="template_id"):
        manager.get_template("../etc/passwd")

    with pytest.raises(ValueError, match="template_id"):
        manager.get_template("..")

    # get_run_state validates run_id
    with pytest.raises(ValueError, match="run_id"):
        manager.get_run_state("../etc/passwd")

    with pytest.raises(ValueError, match="run_id"):
        manager.get_run_state("..")

    # compile_prompt_plan validates flow_id and run_id
    with pytest.raises(ValueError, match="flow_id"):
        manager.compile_prompt_plan("../bad", "step")

    with pytest.raises(ValueError, match="run_id"):
        manager.compile_prompt_plan("valid_flow", "step", run_id="../bad")


def test_run_state_manager_path_validation(tmp_path):
    """Test that RunStateManager validates path components against traversal."""
    import asyncio

    from swarm.api.services.run_state import RunStateManager

    manager = RunStateManager(runs_root=tmp_path)

    async def run_tests():
        # create_run validates flow_id and run_id
        with pytest.raises(ValueError, match="flow_id"):
            await manager.create_run("../etc/passwd")

        with pytest.raises(ValueError, match="run_id"):
            await manager.create_run("valid_flow", run_id="../etc/passwd")

        with pytest.raises(ValueError, match="flow_id"):
            await manager.create_run("..")

        # get_run validates run_id
        with pytest.raises(ValueError, match="run_id"):
            await manager.get_run("../etc/passwd")

        with pytest.raises(ValueError, match="run_id"):
            await manager.get_run("..")

        # update_run validates run_id
        with pytest.raises(ValueError, match="run_id"):
            await manager.update_run("../etc/passwd", {"status": "running"})

        with pytest.raises(ValueError, match="run_id"):
            await manager.update_run("..", {"status": "running"})

    asyncio.run(run_tests())

def test_run_tailer_path_validation(tmp_path):
    """Test that RunTailer validates run_id against path traversal."""
    from swarm.runtime.db import StatsDB
    from swarm.runtime.run_tailer import RunTailer

    # Mock DB or use dummy
    db = StatsDB(db_path=None)
    tailer = RunTailer(db, tmp_path)

    with pytest.raises(ValueError, match="run_id"):
        tailer.tail_run("../etc/passwd")

    with pytest.raises(ValueError, match="run_id"):
        tailer.tail_run("..\\windows\\system32")

    with pytest.raises(ValueError, match="run_id"):
        tailer.tail_run("..")


def test_evolution_api_path_traversal():
    """Test that the Evolution API prevents path traversal via run_id and patch_id."""
    # Test path traversal in get_run_evolution_patches
    response = client.get("/api/evolution/%2e%2e%5cetc")
    assert response.status_code == 400
    assert "invalid_path_parameter" in response.json()["detail"]["error"]

    # Test path traversal in get_evolution_patch_details (run_id)
    response = client.get("/api/evolution/%2e%2e%5cetc/valid-patch-id")
    assert response.status_code == 400

    # Test path traversal in get_evolution_patch_details (patch_id)
    response = client.get("/api/evolution/valid-run-id/%2e%2e%5cetc")
    assert response.status_code == 400

    # Test path traversal in validate_evolution_patch_endpoint
    response = client.post("/api/evolution/valid-run-id/validate/%2e%2e%5cetc")
    assert response.status_code == 400

    # Test path traversal in apply_evolution_patch_endpoint (composite ID)
    response = client.post(
        "/api/evolution/apply",
        json={
            "patch_id": "valid-run-id:%2e%2e%5cetc",
            "dry_run": True,
            "create_backup": True,
        }
    )
    assert response.status_code == 400

    # Test path traversal in apply_evolution_patch_endpoint (patch_id only)
    response = client.post(
        "/api/evolution/apply",
        json={
            "patch_id": "%2e%2e%5cetc",
            "dry_run": True,
            "create_backup": True,
        }
    )
    assert response.status_code == 400

    # Test path traversal in reject_evolution_patch_endpoint
    response = client.post(
        "/api/evolution/valid-run-id/reject/%2e%2e%5cetc",
        json={
            "patch_id": "%2e%2e%5cetc",
            "reason": "Test reason"
        }
    )
    assert response.status_code == 400


def test_wisdom_api_path_traversal():
    """Test that the Wisdom API prevents path traversal via run_id and artifact_name."""
    # Test path traversal in get_wisdom_artifacts
    response = client.get("/api/wisdom/%2e%2e%5cetc")
    assert response.status_code == 400
    assert "invalid_path_parameter" in response.json()["detail"]["error"]

    # Test path traversal in get_wisdom_content (run_id)
    response = client.get("/api/wisdom/%2e%2e%5cetc/valid-artifact.md")
    assert response.status_code == 400

    # Test path traversal in get_wisdom_content (artifact_name)
    response = client.get("/api/wisdom/valid-run-id/%2e%2e%5cetc")
    assert response.status_code == 400

    # Test path traversal in apply_wisdom_patch
    response = client.post(
        "/api/wisdom/valid-run-id/apply",
        json={
            "artifact_name": "%2e%2e%5cetc",
            "dry_run": True,
        }
    )
    assert response.status_code == 400

    # Test path traversal in reject_wisdom_patch
    response = client.post(
        "/api/wisdom/valid-run-id/reject",
        json={
            "artifact_name": "%2e%2e%5cetc",
            "reason": "Test reason"
        }
    )
    assert response.status_code == 400

    # Test path traversal in apply_wisdom_patches
    response = client.post(
        "/api/wisdom/%2e%2e%5cetc/apply-patches",
        json={
            "dry_run": True,
            "patch_type": "flow_evolution",
            "policy": "safe"
        }
    )
    assert response.status_code == 400
