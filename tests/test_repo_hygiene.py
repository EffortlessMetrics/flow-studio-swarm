"""Repo hygiene tests - prevent accidental tracking of temp files."""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_tmpclaude_files_tracked():
    """Fail if any tmpclaude-* files are tracked by git."""
    result = subprocess.run(
        ["git", "ls-files", "tmpclaude-*"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    tracked = result.stdout.strip()
    assert not tracked, (
        f"Temp files are tracked by git: {tracked}\n"
        "Remove with: git rm --cached <files>"
    )
