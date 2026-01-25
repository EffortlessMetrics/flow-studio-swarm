import pytest
from swarm.runtime import storage
from swarm.runtime.safe_paths import validate_path_component
from swarm.tools.flow_studio.services import run_artifacts
from swarm.tools.run_inspector import RunInspector


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
        tailer.tail_run("..")

def test_validate_evolution_patch_traversal(tmp_path):
    """Test that EvolutionPatch validation rejects path traversal."""
    from swarm.runtime.evolution import validate_evolution_patch, EvolutionPatch, PatchType, ConfidenceLevel

    # Setup repo root
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "safe.txt").write_text("safe")

    # Sensitive file outside repo
    sensitive = tmp_path / "sensitive.txt"
    sensitive.write_text("secret")

    # Case 1: Traversal
    patch_traversal = EvolutionPatch(
        id="TEST-001",
        target_file="../sensitive.txt",
        patch_type=PatchType.CONFIG,
        content="hack",
        confidence=ConfidenceLevel.LOW,
        reasoning="test",
    )

    result = validate_evolution_patch(patch_traversal, repo_root=repo_root)
    assert not result.valid
    assert any("escapes repository root" in err for err in result.errors)

    # Case 2: Absolute path
    patch_absolute = EvolutionPatch(
        id="TEST-002",
        target_file=str(sensitive.resolve()),
        patch_type=PatchType.CONFIG,
        content="hack",
        confidence=ConfidenceLevel.LOW,
        reasoning="test",
    )

    result = validate_evolution_patch(patch_absolute, repo_root=repo_root)
    assert not result.valid
    assert any("escapes repository root" in err for err in result.errors)

    # Case 3: Valid relative path
    patch_valid = EvolutionPatch(
        id="TEST-003",
        target_file="safe.txt",
        patch_type=PatchType.CONFIG,
        content="safe update",
        confidence=ConfidenceLevel.LOW,
        reasoning="test",
    )

    result = validate_evolution_patch(patch_valid, repo_root=repo_root)
    # It might fail due to other validations (e.g. content) but not traversal
    for err in result.errors:
        assert "escapes repository root" not in err
