import re

with open('tests/test_shadow_fork.py', 'r') as f:
    content = f.read()

# Fix StopIteration error by returning a function that handles varying calls dynamically.
new_func = '''    def test_create_fails_if_base_branch_missing(self, tmp_path):
        """Test that create fails if base branch doesn't exist."""
        fork = ShadowFork(repo_root=tmp_path)

        def mock_git_side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "rev-parse":
                return (True, "main", "")
            elif cmd[0] == "status":
                return (True, "", "")
            elif cmd[0] == "checkout" and "-b" not in cmd:
                return (False, "", "fatal")
            elif cmd[0] == "checkout" and "-b" in cmd:
                return (False, "", "fatal") # Mock the case where checkout to non-existent base fails.
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=mock_git_side_effect):
            with pytest.raises(RuntimeError, match="does not exist"):
                fork.create(base_branch="nonexistent")

    def test_create_warns_on_uncommitted_changes(self, tmp_path, caplog):
        """Test that create warns about uncommitted changes."""
        fork = ShadowFork(repo_root=tmp_path)

        def mock_git_side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "rev-parse":
                return (True, "main", "")
            elif cmd[0] == "status":
                return (True, " M file.txt", "")
            return (True, "", "")

        with patch.object(fork, "_run_git", side_effect=mock_git_side_effect):
            # Create hooks directory for the test
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            fork.create()

            assert "uncommitted changes" in caplog.text.lower()'''

old_func = '''    def test_create_fails_if_base_branch_missing(self, tmp_path):
        """Test that create fails if base branch doesn't exist."""
        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "main", ""),  # Get current branch
                (True, "", ""),  # Check for uncommitted changes
                (False, "", "fatal"),  # Base branch doesn't exist
            ]

            with pytest.raises(RuntimeError, match="does not exist"):
                fork.create(base_branch="nonexistent")

    def test_create_warns_on_uncommitted_changes(self, tmp_path, caplog):
        """Test that create warns about uncommitted changes."""
        fork = ShadowFork(repo_root=tmp_path)

        with patch.object(fork, "_run_git") as mock_git:
            mock_git.side_effect = [
                (True, "main", ""),  # Get current branch
                (True, " M file.txt", ""),  # Uncommitted changes exist
                (True, "", ""),  # Verify base branch exists
                (True, "", ""),  # Create and switch to shadow branch
            ]

            # Create hooks directory for the test
            (tmp_path / ".git" / "hooks").mkdir(parents=True)

            fork.create()

            assert "uncommitted changes" in caplog.text.lower()'''

content = content.replace(old_func, new_func)

with open('tests/test_shadow_fork.py', 'w') as f:
    f.write(content)
