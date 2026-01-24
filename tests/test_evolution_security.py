"""Security tests for evolution module."""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys

_SWARM_ROOT = Path(__file__).resolve().parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from swarm.runtime.evolution import (
    EvolutionPatch,
    PatchType,
    ConfidenceLevel,
    apply_evolution_patch,
    validate_evolution_patch
)

@pytest.fixture
def temp_repo_structure():
    """Create a temp repo and a file outside it."""
    base_dir = Path(tempfile.mkdtemp())
    repo_root = base_dir / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    outside_file = base_dir / "secret.txt"
    outside_file.write_text("SECRET")

    yield repo_root, outside_file

    shutil.rmtree(base_dir)

def test_evolution_path_traversal(temp_repo_structure):
    """Test that applying a patch with '..' is rejected."""
    repo_root, outside_file = temp_repo_structure

    # Construct a path like ../secret.txt
    rel_path = f"../{outside_file.name}"

    patch = EvolutionPatch(
        id="ATTACK-001",
        target_file=rel_path,
        patch_type=PatchType.CONFIG,
        content="HACKED",
        confidence=ConfidenceLevel.HIGH,
        reasoning="Traversal attack"
    )

    # Test validation
    result = validate_evolution_patch(patch, repo_root=repo_root)
    assert result.valid is False
    assert any("outside repository" in e for e in result.errors)

    # Test application
    app_result = apply_evolution_patch(patch, dry_run=False, repo_root=repo_root)
    assert app_result.success is False
    assert any("outside repository" in e for e in app_result.errors)

    # Verify file untouched
    assert outside_file.read_text() == "SECRET"

def test_evolution_absolute_path(temp_repo_structure):
    """Test that applying a patch with absolute path is rejected."""
    repo_root, outside_file = temp_repo_structure

    patch = EvolutionPatch(
        id="ATTACK-002",
        target_file=str(outside_file), # Absolute path
        patch_type=PatchType.CONFIG,
        content="HACKED",
        confidence=ConfidenceLevel.HIGH,
        reasoning="Absolute path attack"
    )

    result = validate_evolution_patch(patch, repo_root=repo_root)
    assert result.valid is False
    assert any("outside repository" in e for e in result.errors)

    app_result = apply_evolution_patch(patch, dry_run=False, repo_root=repo_root)
    assert app_result.success is False

    assert outside_file.read_text() == "SECRET"

def test_evolution_valid_path(temp_repo_structure):
    """Test that valid paths inside repo are accepted."""
    repo_root, _ = temp_repo_structure

    target_file = repo_root / "config.yaml"
    target_file.write_text("old: value")

    patch = EvolutionPatch(
        id="VALID-001",
        target_file="config.yaml",
        patch_type=PatchType.CONFIG,
        content="new: value",
        confidence=ConfidenceLevel.HIGH,
        reasoning="Valid update"
    )

    result = validate_evolution_patch(patch, repo_root=repo_root)
    assert result.valid is True

    app_result = apply_evolution_patch(patch, dry_run=False, repo_root=repo_root)
    assert app_result.success is True
    assert "new: value" in target_file.read_text()

def test_evolution_new_file_valid(temp_repo_structure):
    """Test that creating a new file inside repo is accepted."""
    repo_root, _ = temp_repo_structure

    patch = EvolutionPatch(
        id="NEW-001",
        target_file="new_config.yaml",
        patch_type=PatchType.CONFIG,
        content="created: true",
        confidence=ConfidenceLevel.HIGH,
        reasoning="New file"
    )

    result = validate_evolution_patch(patch, repo_root=repo_root)
    assert result.valid is True

    app_result = apply_evolution_patch(patch, dry_run=False, repo_root=repo_root)
    assert app_result.success is True
    assert (repo_root / "new_config.yaml").read_text().strip() == "created: true"
