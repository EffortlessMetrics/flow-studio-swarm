"""
Core tests for the shadow_fork module.

Tests initialization, creation, cleanup, and file locking.
"""

from unittest.mock import patch

import pytest
from swarm.runtime.shadow_fork import (
    MARKER_FILE,
    PRE_PUSH_HOOK_MARKER,
    SHADOW_BRANCH_PREFIX,
    ShadowFork,
    load_shadow_state,
)


class TestShadowForkBasics:
    """Basic tests for ShadowFork dataclass."""

    def test_initialization(self, tmp_path):
        """Test creating a ShadowFork instance."""
        fork = ShadowFork(repo_root=tmp_path)
        assert fork.repo_root == tmp_path
        assert fork.shadow_branch is None
        assert fork.original_branch is None
        assert fork.base_branch == "main"
        assert fork._push_allowed is False

    def test_custom_base_branch(self, tmp_path):
        """Test creating with custom base branch."""
        fork = ShadowFork(repo_root=tmp_path, base_branch="develop")
        assert fork.base_branch == "develop"


class TestShadowForkCreate:
    """Tests for shadow fork creation."""

    def test_create_success(self, tmp_path):
        """Test successful shadow fork creation."""
        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "main", ""),  # Get current branch
                (True, "", ""),  # Check for uncommitted changes
                (True, "", ""),  # Verify base branch exists
                (True, "", ""),  # Create and switch to shadow branch
                (True, "", ""),  # Install push guard (rev-parse in block_upstream_push)
            ]

            # Create hooks directory for the test
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            branch = fork.create(base_branch="main")

            assert branch.startswith(SHADOW_BRANCH_PREFIX)
            assert fork.shadow_branch == branch
            assert fork.original_branch == "main"
            assert (tmp_path / MARKER_FILE).exists()

    def test_create_fails_if_already_active(self, tmp_path):
        """Test that create fails if shadow fork is already active."""
        # Create marker file
        marker = tmp_path / MARKER_FILE
        marker.write_text("shadow_branch=shadow/12345")

        fork = ShadowFork(repo_root=tmp_path)

        with pytest.raises(RuntimeError, match="Shadow fork already active"):
            fork.create()

    def test_create_fails_if_base_branch_missing(self, tmp_path):
        """Test that create fails if base branch doesn't exist."""
        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "main", ""),  # Get current branch
                (True, "", ""),  # Resolve base ref (first attempt)
                (True, "", ""),  # Check for uncommitted changes
                (False, "", "fatal: 'nonexistent' does not exist"),  # Checkout fails
            ]

            with pytest.raises(RuntimeError, match="does not exist"):
                fork.create(base_branch="nonexistent")

    def test_create_warns_on_uncommitted_changes(self, tmp_path, caplog):
        """Test that create warns about uncommitted changes."""
        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "main", ""),  # Get current branch
                (True, "", ""),  # Resolve base ref
                (True, " M file.txt", ""),  # Uncommitted changes exist
                (True, "", ""),  # Create and switch to shadow branch
            ]

            # Create hooks directory for the test
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            fork.create()

            assert "uncommitted changes" in caplog.text.lower()


class TestShadowForkCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_success(self, tmp_path):
        """Test cleanup after successful run."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
            original_branch="main",
            base_branch="main",
        )

        # Create marker file
        marker = tmp_path / MARKER_FILE
        marker.write_text("test")

        # Create hooks directory
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "shadow/test", ""),  # Get current branch
                (True, "", ""),  # Checkout base branch
                (True, "", ""),  # Delete shadow branch
            ]

            fork.cleanup(success=True)

            assert not marker.exists()
            assert fork.shadow_branch is None

    def test_cleanup_failure(self, tmp_path):
        """Test cleanup after failed run."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
            original_branch="feature-x",
            base_branch="main",
        )

        # Create marker file
        marker = tmp_path / MARKER_FILE
        marker.write_text("test")

        # Create hooks directory
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "shadow/test", ""),  # Get current branch
                (True, "", ""),  # Checkout original branch
                (True, "", ""),  # Delete shadow branch
            ]

            fork.cleanup(success=False)

            assert not marker.exists()
            assert fork.shadow_branch is None
            # Should have tried to checkout original branch
            mock_git.assert_any_call(["checkout", "feature-x"], check=False)


class TestLoadShadowState:
    """Tests for loading shadow fork state."""

    def test_load_existing_state(self, tmp_path):
        """Test loading existing shadow fork state."""
        marker = tmp_path / MARKER_FILE
        marker.write_text(
            "shadow_branch=shadow/20251230-120000\n"
            "original_branch=feature-x\n"
            "base_branch=main\n"
            "created_at=2025-12-30T12:00:00+00:00\n"
        )

        fork = load_shadow_state(tmp_path)

        assert fork is not None
        assert fork.shadow_branch == "shadow/20251230-120000"
        assert fork.original_branch == "feature-x"
        assert fork.base_branch == "main"

    def test_load_no_state(self, tmp_path):
        """Test loading when no shadow fork is active."""
        fork = load_shadow_state(tmp_path)

        assert fork is None
