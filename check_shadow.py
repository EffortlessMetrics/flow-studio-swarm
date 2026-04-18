import pytest
from unittest.mock import patch
from swarm.runtime.shadow_fork import ShadowFork

def run_test(tmp_path):
    fork = ShadowFork(repo_root=tmp_path)
    with patch.object(fork, "_run_git") as mock_git:
        mock_git.side_effect = [
            (True, "main", ""),  # Get current branch
            (True, "main", ""),  # check branch exists
            (True, " M file.txt", ""),  # Uncommitted changes exist
            (True, "", ""),  # Verify base branch exists
            (True, "", ""),  # Create and switch to shadow branch
            (True, "", "")
        ]
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        try:
            fork.create()
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
