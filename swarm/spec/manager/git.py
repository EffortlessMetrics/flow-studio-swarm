from __future__ import annotations

import logging
from pathlib import Path


def git_commit(
    repo_root: Path,
    path: Path,
    message: str,
    logger: logging.Logger,
) -> bool:
    """Commit a file change to git."""
    try:
        import subprocess

        # Stage the file
        rel_path = path.relative_to(repo_root)
        subprocess.run(
            ["git", "add", str(rel_path)],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )

        logger.info("Git commit: %s", message)
        return True

    except Exception as e:
        logger.warning("Git commit failed: %s", e)
        return False
