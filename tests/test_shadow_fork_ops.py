"""
Operational tests for the shadow_fork module.

Tests diffs, checkpoints, rollbacks, bridging, and integration workflows.
"""

from unittest.mock import patch

import pytest
from swarm.runtime.shadow_fork import (
    MARKER_FILE,
    PRE_PUSH_HOOK_MARKER,
    SHADOW_BRANCH_PREFIX,
    ShadowFork,
)


class TestShadowForkGetDiff:
    """Tests for getting diff against base branch."""

    def test_get_diff_success(self, tmp_path):
        """Test successful diff retrieval."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
            base_branch="main",
        )

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.return_value = (True, "+new line\n-old line", "")

            diff = fork.get_diff()

            assert "+new line" in diff
            assert "-old line" in diff

    def test_get_diff_no_shadow(self, tmp_path, caplog):
        """Test get_diff when no shadow branch is active."""
        fork = ShadowFork(repo_root=tmp_path)

        diff = fork.get_diff()

        assert diff == ""
        assert "No shadow branch active" in caplog.text


class TestShadowForkCheckpoint:
    """Tests for checkpoint creation."""

    def test_commit_checkpoint_success(self, tmp_path):
        """Test successful checkpoint creation."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
        )

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "", ""),  # git add -A
                (False, "", ""),  # git diff --cached --quiet (has changes)
                (True, "", ""),  # git commit
                (True, "abc123", ""),  # git rev-parse HEAD
            ]

            sha = fork.commit_checkpoint("test checkpoint")

            assert sha == "abc123"

    def test_commit_checkpoint_no_changes(self, tmp_path):
        """Test checkpoint when there are no changes."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
        )

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "", ""),  # git add -A
                (True, "", ""),  # git diff --cached --quiet (no changes)
                (True, "def456", ""),  # git rev-parse HEAD (current)
            ]

            sha = fork.commit_checkpoint("no changes")

            assert sha == "def456"

    def test_commit_checkpoint_no_shadow(self, tmp_path):
        """Test checkpoint fails when no shadow branch is active."""
        fork = ShadowFork(repo_root=tmp_path)

        with pytest.raises(RuntimeError, match="No shadow branch active"):
            fork.commit_checkpoint("test")


class TestShadowForkRollback:
    """Tests for rollback functionality."""

    def test_rollback_success(self, tmp_path):
        """Test successful rollback."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
        )

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "", ""),  # Verify commit exists
                (True, "", ""),  # Hard reset
            ]

            result = fork.rollback_to("abc123")

            assert result is True
            mock_git.assert_any_call(["reset", "--hard", "abc123"])

    def test_rollback_commit_not_found(self, tmp_path):
        """Test rollback fails when commit doesn't exist."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
        )

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.return_value = (False, "", "bad object")

            result = fork.rollback_to("nonexistent")

            assert result is False

    def test_rollback_no_shadow(self, tmp_path):
        """Test rollback fails when no shadow branch is active."""
        fork = ShadowFork(repo_root=tmp_path)

        result = fork.rollback_to("abc123")

        assert result is False


class TestShadowForkBridge:
    """Tests for bridging to main."""

    def test_bridge_success(self, tmp_path):
        """Test successful bridge to main."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
            base_branch="main",
        )
        fork._push_allowed = True

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "", ""),  # Checkout main
                (True, "", ""),  # Merge shadow branch
            ]

            result = fork.bridge_to_main()

            assert result is True

    def test_bridge_fails_without_allow_push(self, tmp_path):
        """Test bridge fails when push is not allowed."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
        )

        result = fork.bridge_to_main()

        assert result is False

    def test_bridge_no_shadow(self, tmp_path):
        """Test bridge fails when no shadow branch is active."""
        fork = ShadowFork(repo_root=tmp_path)

        result = fork.bridge_to_main()

        assert result is False


class TestShadowForkPushGuard:
    """Tests for push guard functionality."""

    def test_block_upstream_push(self, tmp_path):
        """Test installing push guard hook."""
        fork = ShadowFork(repo_root=tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)

        fork.block_upstream_push()

        hook_path = hooks_dir / "pre-push"
        assert hook_path.exists()
        content = hook_path.read_text(encoding="utf-8")
        assert PRE_PUSH_HOOK_MARKER in content
        assert MARKER_FILE in content

    def test_block_upstream_push_appends_to_existing(self, tmp_path):
        """Test that push guard appends to existing hook."""
        fork = ShadowFork(repo_root=tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook_path = hooks_dir / "pre-push"
        hook_path.write_text("#!/bin/sh\necho 'existing hook'\n")

        fork.block_upstream_push()

        content = hook_path.read_text(encoding="utf-8")
        assert "existing hook" in content
        assert PRE_PUSH_HOOK_MARKER in content

    def test_allow_push(self, tmp_path):
        """Test removing push guard."""
        fork = ShadowFork(repo_root=tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)

        # Install guard first
        fork.block_upstream_push()

        # Now allow push
        fork.allow_push()

        hook_path = hooks_dir / "pre-push"
        # Hook should be removed if it was only our guard
        assert not hook_path.exists() or PRE_PUSH_HOOK_MARKER not in hook_path.read_text(
            encoding="utf-8"
        )
        assert fork._push_allowed is True


class TestShadowForkIntegration:
    """Integration tests for the full shadow fork workflow."""

    def test_full_workflow_success(self, tmp_path):
        """Test complete success workflow: create -> checkpoint -> bridge -> cleanup."""
        # Create hooks directory
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git") as mock_git:
            # Create shadow
            mock_git.side_effect = [
                (True, "main", ""),  # Get current branch
                (True, "", ""),  # Check uncommitted changes
                (True, "", ""),  # Verify base branch
                (True, "", ""),  # Create shadow branch
            ]
            branch = fork.create()
            assert branch.startswith(SHADOW_BRANCH_PREFIX)

            # Checkpoint
            mock_git.side_effect = [
                (True, "", ""),  # git add
                (False, "", ""),  # git diff (has changes)
                (True, "", ""),  # git commit
                (True, "abc123", ""),  # git rev-parse
            ]
            sha = fork.commit_checkpoint("WIP")
            assert sha == "abc123"

            # Bridge to main
            fork._push_allowed = True
            mock_git.side_effect = [
                (True, "", ""),  # Checkout main
                (True, "", ""),  # Merge
            ]
            result = fork.bridge_to_main()
            assert result is True

            # Cleanup
            mock_git.side_effect = [
                (True, "main", ""),  # Get current branch
                (True, "", ""),  # Delete shadow branch
            ]
            fork.cleanup(success=True)
            assert fork.shadow_branch is None

    def test_full_workflow_failure(self, tmp_path):
        """Test complete failure workflow: create -> checkpoint -> rollback -> cleanup."""
        # Create hooks directory
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git") as mock_git:
            # Create shadow
            mock_git.side_effect = [
                (True, "feature-x", ""),  # Get current branch
                (True, "", ""),  # Check uncommitted changes
                (True, "", ""),  # Verify base branch
                (True, "", ""),  # Create shadow branch
            ]
            fork.create()

            # Checkpoint
            mock_git.side_effect = [
                (True, "", ""),  # git add
                (False, "", ""),  # git diff (has changes)
                (True, "", ""),  # git commit
                (True, "abc123", ""),  # git rev-parse
            ]
            sha = fork.commit_checkpoint("WIP")

            # Rollback
            mock_git.side_effect = [
                (True, "", ""),  # Verify commit
                (True, "", ""),  # Hard reset
            ]
            result = fork.rollback_to(sha)
            assert result is True

            # Cleanup (failure case)
            mock_git.side_effect = [
                (True, fork.shadow_branch, ""),  # Get current branch
                (True, "", ""),  # Checkout original
                (True, "", ""),  # Delete shadow
            ]
            fork.cleanup(success=False)
            assert fork.shadow_branch is None
