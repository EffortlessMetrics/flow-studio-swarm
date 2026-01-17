# swarm/tools/validation/git_helpers.py
"""Git-related helpers for incremental validation (FR-011)."""

import subprocess
from pathlib import Path
from typing import Optional, Set

from .helpers import ROOT


def get_modified_files() -> Optional[Set[str]]:
    """
    Get list of modified files from git, including uncommitted changes.

    Resolves default branch dynamically (origin/HEAD or fallback to main).
    Includes both committed and uncommitted changes relative to base branch.

    Returns set of file paths relative to repo root, or None if git unavailable.
    Returns an empty set when the repo is clean.
    """
    try:
        def _ref_exists(ref: str) -> bool:
            """Check if a git ref exists (local or remote)."""
            result = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", ref],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0

        # Resolve default branch dynamically
        base_branch: Optional[str] = None
        try:
            # Try to get the default branch from origin/HEAD
            result = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Result is like "refs/remotes/origin/main"
                ref = result.stdout.strip().split("/")[-1]
                if ref:
                    base_branch = ref
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Use fallback

        # Fall back to common default branches if origin/HEAD is unavailable
        if base_branch is None:
            for ref in (
                "refs/remotes/origin/main",
                "refs/remotes/origin/master",
                "refs/heads/main",
                "refs/heads/master",
            ):
                if _ref_exists(ref):
                    # Keep remote prefix (origin/main) when present
                    base_branch = ref.replace("refs/remotes/", "").replace("refs/heads/", "")
                    break

        if base_branch is None:
            base_branch = "main"

        # Get modified files including uncommitted changes
        # git diff <base> (without HEAD) shows both staged and unstaged changes
        diff_output: Optional[str] = None
        for target in [base_branch, "HEAD"] if base_branch != "HEAD" else [base_branch]:
            result = subprocess.run(
                ["git", "diff", "--name-only", target],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                diff_output = result.stdout
                break

        if diff_output is None:
            return None

        # Parse diff output (includes uncommitted changes)
        files = set(diff_output.strip().splitlines())

        # Also include staged changes (already in git diff, but be explicit)
        # and any modified files from git status
        result_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result_status.returncode == 0:
            # Parse status output (modified/staged/untracked)
            for line in result_status.stdout.splitlines():
                if len(line) > 3:
                    # Status format: "XY filename"
                    # Include any modified (M), added (A), deleted (D), renamed (R), etc.
                    status = line[:2].strip()
                    if status:  # Non-empty status means file was changed
                        files.add(line[3:].split(" -> ")[-1])  # handle renames

        return files
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def should_check_file(file_path: Path, modified_files: Optional[Set[str]]) -> bool:
    """
    Determine if file should be checked based on --check-modified flag.

    Args:
        file_path: Absolute path to file
        modified_files: Set of modified files (None = check all)

    Returns:
        True if file should be checked
    """
    if modified_files is None:
        return True

    try:
        rel_path = str(file_path.relative_to(ROOT))
        return rel_path in modified_files
    except ValueError:
        return True
