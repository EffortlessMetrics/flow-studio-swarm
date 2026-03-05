import logging
from unittest.mock import patch

import pytest
from swarm.runtime.shadow_fork import (
    MARKER_FILE,
    PRE_PUSH_HOOK_MARKER,
    SHADOW_BRANCH_PREFIX,
    ShadowFork,
    load_shadow_state,
)


def build_side_effect(branch="feature-x", has_changes=False, base_exists=True):
    def git_side_effect(args, **kwargs):
        if not args:
            return (True, "", "")
        cmd = args[0]

        if cmd == "branch":
            if "--show-current" in args:
                return (True, branch, "")
            return (True, "", "")

        elif cmd == "diff":
            if "--name-status" in args and "--cached" not in args:
                if has_changes:
                    return (True, " M file.txt", "")
                else:
                    return (True, "", "")
            return (True, "", "")

        elif cmd == "rev-parse":
            if not base_exists and args[-1] == "nonexistent":
                return (False, "", "fatal")
            return (True, "abc12345", "")

        return (True, "", "")

    return git_side_effect


class TestShadowForkBasics:
    """Tests for basic ShadowFork functionality and properties."""

    def test_initialization(self, tmp_path):
        """Test default initialization."""
        fork = ShadowFork(repo_root=tmp_path)
        assert fork.repo_root == tmp_path
        assert fork.base_branch == "main"
        assert fork.shadow_branch is None
        assert fork.original_branch is None

    def test_custom_base_branch(self, tmp_path):
        """Test initialization with custom base branch."""
        fork = ShadowFork(repo_root=tmp_path, base_branch="develop")
        assert fork.base_branch == "develop"


class TestShadowForkCreate:
    """Tests for creating a shadow fork."""

    def test_create_success(self, tmp_path):
        """Test successful creation of shadow fork."""
        fork = ShadowFork(repo_root=tmp_path)

        def git_side_effect(args, **kwargs):
            cmd = args[0] if args else ""
            if cmd == "rev-parse":
                if "--abbrev-ref" in args and "HEAD" in args:
                    return (True, "feature-x", "")
                return (True, "", "")
            elif cmd == "diff":
                return (True, "", "")
            elif cmd == "branch":
                return (True, "", "")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=git_side_effect):
            # Create hooks directory for the test
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            shadow_branch = fork.create()

            assert shadow_branch is not None
            assert shadow_branch.startswith(SHADOW_BRANCH_PREFIX)
            assert fork.shadow_branch == shadow_branch
            assert fork.original_branch == "feature-x"

            # Verify marker file was created
            marker_path = tmp_path / MARKER_FILE
            assert marker_path.exists()
            content = marker_path.read_text()
            assert f"shadow_branch={shadow_branch}" in content
            assert "original_branch=feature-x" in content

    def test_create_fails_if_already_active(self, tmp_path):
        """Test that create fails if a shadow fork is already active."""
        fork = ShadowFork(repo_root=tmp_path)

        # Create marker file to simulate active shadow fork
        marker_path = tmp_path / MARKER_FILE
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text("shadow_branch=shadow/test\n")

        with pytest.raises(RuntimeError, match="already active"):
            fork.create()

    def test_create_fails_if_base_branch_missing(self, tmp_path):
        """Test that create fails if base branch doesn't exist."""
        fork = ShadowFork(repo_root=tmp_path)

        def git_side_effect(args, **kwargs):
            cmd = args[0] if args else ""
            if cmd == "rev-parse":
                return (False, "", "fatal")
            if cmd == "checkout" and "-b" in args:
                return (False, "", "fatal")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=git_side_effect):
            with pytest.raises(RuntimeError, match="Failed to create shadow branch"):
                fork.create(base_branch="nonexistent")

    def test_create_warns_on_uncommitted_changes(self, tmp_path, caplog):
        """Test that create warns about uncommitted changes."""
        caplog.set_level(logging.WARNING, logger="swarm.runtime.shadow_fork")
        fork = ShadowFork(repo_root=tmp_path)

        def git_side_effect(args, **kwargs):
            cmd = args[0] if args else ""
            if cmd == "rev-parse":
                if "--abbrev-ref" in args:
                    return (True, "main", "")
                return (True, "", "")
            elif cmd == "status":
                if "--porcelain" in args:
                    return (True, " M file.txt", "")
                return (True, "", "")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=git_side_effect):
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

        def mock_side_effect(args, **kwargs):
            if args[0] == "diff":
                return (False, "", "")  # has changes
            elif args[0] == "rev-parse":
                return (True, "abc12345", "")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=mock_side_effect):
            sha = fork.commit_checkpoint("test checkpoint")
            assert sha == "abc12345"

    def test_commit_checkpoint_no_changes(self, tmp_path):
        """Test checkpoint when there are no changes."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
        )

        def mock_side_effect(args, **kwargs):
            if args[0] == "diff":
                return (True, "", "")  # no changes
            elif args[0] == "rev-parse":
                return (True, "def456", "")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=mock_side_effect):
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
            mock_git.return_value = (True, "", "")

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
            mock_git.return_value = (True, "", "")

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
    """Tests for push guard installation."""

    def test_block_upstream_push(self, tmp_path):
        """Test installing the push guard."""
        fork = ShadowFork(repo_root=tmp_path)
        hook_path = tmp_path / ".git" / "hooks" / "pre-push"

        fork.block_upstream_push()

        assert hook_path.exists()
        assert PRE_PUSH_HOOK_MARKER in hook_path.read_text()

    def test_block_upstream_push_appends_to_existing(self, tmp_path):
        """Test appending guard to existing hook."""
        fork = ShadowFork(repo_root=tmp_path)
        hook_path = tmp_path / ".git" / "hooks" / "pre-push"

        hook_path.parent.mkdir(parents=True)
        hook_path.write_text("#!/bin/sh\necho 'custom'\n")

        fork.block_upstream_push()

        content = hook_path.read_text()
        assert "echo 'custom'" in content
        assert PRE_PUSH_HOOK_MARKER in content

    def test_allow_push(self, tmp_path):
        """Test removing the push guard."""
        fork = ShadowFork(repo_root=tmp_path)
        fork.block_upstream_push()

        fork.allow_push()

        hook_path = tmp_path / ".git" / "hooks" / "pre-push"
        if hook_path.exists():
            assert PRE_PUSH_HOOK_MARKER not in hook_path.read_text()
        assert fork._push_allowed is True


class TestShadowForkCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_success(self, tmp_path):
        """Test cleanup after successful run."""
        fork = ShadowFork(
            repo_root=tmp_path,
            shadow_branch="shadow/test",
            original_branch="feature-x",
            base_branch="main",
        )

        # Create marker file
        marker = tmp_path / MARKER_FILE
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("test")

        # Create hooks directory
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        with patch.object(fork, "_run_git", side_effect=build_side_effect(branch="shadow/test")):
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
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("test")

        # Create hooks directory
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        def git_side_effect(args, **kwargs):
            cmd = args[0] if args else ""
            if cmd == "rev-parse" and "--abbrev-ref" in args:
                return (True, "shadow/test", "")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=git_side_effect) as mock_git:
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
        marker.parent.mkdir(parents=True, exist_ok=True)
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
        """Test loading when no state exists returns None."""
        fork = load_shadow_state(tmp_path)
        assert fork is None


class TestShadowForkIntegration:
    """Integration style tests exercising the full lifecycle."""

    def test_full_workflow_success(self, tmp_path):
        """Test full shadow fork lifecycle on success path."""
        fork = ShadowFork(repo_root=tmp_path)

        def mock_side_effect(args, **kwargs):
            if not args:
                return (True, "", "")
            cmd = args[0]
            if cmd == "branch":
                return (True, "main", "")
            elif cmd == "diff":
                if "--cached" in args:
                    return (False, "", "")  # has changes
                return (True, "", "")
            elif cmd == "rev-parse":
                return (True, "abc12345", "")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=mock_side_effect):
            # Create hooks dir
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            # Create shadow
            branch = fork.create()
            assert branch.startswith(SHADOW_BRANCH_PREFIX)

            # Checkpoint
            sha = fork.commit_checkpoint("WIP")
            assert sha == "abc12345"

            # Bridge to main
            fork.allow_push()
            result = fork.bridge_to_main()
            assert result is True

            # Cleanup
            fork.cleanup(success=True)
            assert fork.shadow_branch is None
            assert not (tmp_path / MARKER_FILE).exists()

    def test_full_workflow_failure(self, tmp_path):
        """Test full shadow fork lifecycle on failure path."""
        fork = ShadowFork(repo_root=tmp_path)

        def mock_side_effect(args, **kwargs):
            if not args:
                return (True, "", "")
            cmd = args[0]
            if cmd == "branch":
                if fork.shadow_branch and args[-1] == "--show-current":
                    return (True, fork.shadow_branch, "")
                return (True, "feature-x", "")
            elif cmd == "diff":
                if "--cached" in args:
                    return (False, "", "")
                return (True, "", "")
            elif cmd == "rev-parse":
                return (True, "abc12345", "")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=mock_side_effect):
            # Create hooks dir
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            # Create shadow
            fork.create()

            # Checkpoint
            sha = fork.commit_checkpoint("WIP")

            # Rollback
            result = fork.rollback_to(sha)
            assert result is True

            # Cleanup (failure case)
            fork.cleanup(success=False)
            assert fork.shadow_branch is None
