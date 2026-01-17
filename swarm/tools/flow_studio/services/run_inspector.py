from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def create_run_inspector(repo_root: Path) -> Optional[Any]:
    try:
        from swarm.tools.run_inspector import RunInspector
    except ImportError:
        return None

    try:
        return RunInspector(repo_root=repo_root)
    except Exception:
        return None
