"""
Tests for the shadow_fork module.

These tests verify the Shadow Fork isolation layer for safe speculative
execution, including branch creation, checkpointing, rollback, and cleanup.
"""

from unittest.mock import patch, MagicMock

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

    def _mock_git_side_effect(self, args, **kwargs):
        """Robust mock for git commands."""
        cmd = args[0]

        if cmd == "rev-parse" and "--abbrev-ref" in args:
            return (True, "main", "")

        if cmd == "rev-parse" and "--verify" in args:
            ref = args[-1]
            if "nonexistent" in ref:
                return (False, "", "fatal: needed single revision")
            return (True, "abc12345", "")

        if cmd == "status" and "--porcelain" in args:
            # Default to clean state, override in test if needed
            return (True, "", "")

        if cmd == "checkout":
            return (True, "", "")

        if cmd == "add":
            return (True, "", "")

        if cmd == "commit":
            return (True, "", "")

        if cmd == "diff":
            return (True, "", "")

        # Default success
        return (True, "", "")

    def test_create_success(self, tmp_path):
        """Test successful shadow fork creation."""
        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git", side_effect=self._mock_git_side_effect):
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

    def test_create_falls_back_to_head_if_base_branch_missing(self, tmp_path):
        """Test that create falls back to HEAD if base branch doesn't exist."""
        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git", side_effect=self._mock_git_side_effect):
            # Create hooks directory
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            # Should not raise exception
            fork.create(base_branch="nonexistent")

            # Should have fallen back to HEAD (or a valid ref that is not nonexistent)
            # Since our mock returns False for 'nonexistent', it will eventually find 'HEAD' or 'main'
            assert fork.base_branch != "nonexistent"

    def test_create_warns_on_uncommitted_changes(self, tmp_path, caplog):
        """Test that create warns about uncommitted changes."""
        fork = ShadowFork(repo_root=tmp_path)

        def side_effect(args, **kwargs):
            if args[0] == "status":
                return (True, " M file.txt", "")
            return self._mock_git_side_effect(args, **kwargs)

        with patch.object(fork, "_run_git", side_effect=side_effect):
            # Create hooks directory for the test
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            fork.create()

            assert "uncommitted changes" in caplog.text.lower()


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


class TestShadowForkIntegration:
    """Integration tests for the full shadow fork workflow."""

    def _mock_git_side_effect(self, args, **kwargs):
        """Robust mock for git commands integration."""
        cmd = args[0]

        if cmd == "rev-parse" and "--abbrev-ref" in args:
            return (True, "main", "")

        if cmd == "rev-parse" and "--verify" in args:
            return (True, "abc12345", "")

        if cmd == "status" and "--porcelain" in args:
            return (True, "", "")

        if cmd == "diff" and "--cached" in args and "--quiet" in args:
            # By default assume changes (return False for quiet means exit code 1)
            # But here we need to simulate success/failure based on context
            # Let's check call count or context?
            # It's easier to override in specific tests
            return (False, "", "")

        return (True, "", "")

    def test_full_workflow_success(self, tmp_path):
        """Test complete success workflow: create -> checkpoint -> bridge -> cleanup."""
        # Create hooks directory
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git", side_effect=self._mock_git_side_effect) as mock_git:
            # Create shadow
            branch = fork.create()
            assert branch.startswith(SHADOW_BRANCH_PREFIX)

            # Checkpoint
            # Override for checkpoint calls
            def checkpoint_side_effect(args, **kwargs):
                if args[0] == "diff" and "--cached" in args:
                    return (False, "", "") # Has changes
                return self._mock_git_side_effect(args, **kwargs)

            mock_git.side_effect = checkpoint_side_effect
            sha = fork.commit_checkpoint("WIP")
            # assert sha is valid (from mock)

            # Bridge to main
            fork._push_allowed = True
            mock_git.side_effect = self._mock_git_side_effect
            result = fork.bridge_to_main()
            assert result is True

            # Cleanup
            fork.cleanup(success=True)
            assert fork.shadow_branch is None

    def test_full_workflow_failure(self, tmp_path):
        """Test complete failure workflow: create -> checkpoint -> rollback -> cleanup."""
        # Create hooks directory
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git", side_effect=self._mock_git_side_effect) as mock_git:
            # Create shadow
            fork.create()

            # Checkpoint
            def checkpoint_side_effect(args, **kwargs):
                if args[0] == "diff" and "--cached" in args:
                    return (False, "", "") # Has changes
                return self._mock_git_side_effect(args, **kwargs)

            mock_git.side_effect = checkpoint_side_effect
            sha = fork.commit_checkpoint("WIP")

            # Rollback
            mock_git.side_effect = self._mock_git_side_effect
            result = fork.rollback_to(sha)
            assert result is True

            # Cleanup (failure case)
            fork.cleanup(success=False)
            assert fork.shadow_branch is None
