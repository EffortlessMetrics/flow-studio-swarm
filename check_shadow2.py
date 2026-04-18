import pytest
from unittest.mock import patch
from swarm.runtime.shadow_fork import ShadowFork

def run_test(tmp_path):
    fork = ShadowFork(repo_root=tmp_path)
    with patch.object(fork, "_run_git") as mock_git:
        mock_git.side_effect = [
            (True, "main", ""),  # Get current branch
            (False, "", "fatal"),  # _resolve_base_ref -> _ref_exists("nonexistent")
            (False, "", "fatal"),  # _resolve_base_ref -> _ref_exists("origin/nonexistent")
            (False, "", "fatal"),  # _resolve_base_ref -> _ref_exists("main")
            (False, "", "fatal"),  # _resolve_base_ref -> _ref_exists("origin/main")
            (False, "", "fatal"),  # _resolve_base_ref -> _ref_exists("master")
            (False, "", "fatal"),  # _resolve_base_ref -> _ref_exists("origin/master")
            (True, "", ""),  # Check for uncommitted changes
            (False, "", "fatal"),  # Base branch doesn't exist (checkout failure)
            (True, "", "")
        ]
        try:
            fork.create(base_branch="nonexistent")
        except Exception as e:
            print(f"Error: {e}")

        print("Mock calls:")
        for call in mock_git.call_args_list:
            print(call)

if __name__ == "__main__":
    import tempfile
    import pathlib
    with tempfile.TemporaryDirectory() as d:
        run_test(pathlib.Path(d))
