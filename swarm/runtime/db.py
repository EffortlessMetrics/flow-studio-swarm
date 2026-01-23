from __future__ import annotations

"""
db.py - StatsDB compatibility shim.

Re-exports the StatsDB implementation from swarm.runtime.statsdb to preserve
import paths for callers (swarm.runtime.db).
"""

from typing import Optional  # noqa: E402

from swarm.runtime.statsdb import *  # noqa: F403, E402
from swarm.runtime.statsdb import StatsDB  # noqa: E402
from swarm.runtime.statsdb import __all__ as _statsdb_all  # noqa: E402

__all__ = _statsdb_all

# Backward-compatibility shim for tests that monkeypatch _global_db
# The actual global singleton is in swarm.runtime.resilient_db._global_resilient_db
_global_db: Optional[StatsDB] = None


if __name__ == "__main__":
    from swarm.runtime.statsdb.cli import main

    main()
