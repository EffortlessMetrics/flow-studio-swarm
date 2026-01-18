from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from .db import StatsDB

logger = logging.getLogger(__name__)

_global_db: Optional[StatsDB] = None
_global_db_lock = threading.Lock()


def get_stats_db(
    db_path: Optional[Path] = None,
    auto_rebuild: bool = True,
) -> StatsDB:
    """Get the global StatsDB instance.

    Creates a new instance if one doesn't exist, or if a different
    db_path is requested. If the projection version mismatches, the
    old database is renamed and a rebuild from events.jsonl is triggered.

    Args:
        db_path: Path to the DuckDB file. If None, uses default location.
        auto_rebuild: If True (default), automatically rebuild from
            events.jsonl when projection version mismatch is detected.

    Returns:
        The StatsDB instance.
    """
    global _global_db

    with _global_db_lock:
        if _global_db is None:
            if db_path is None:
                # Default to .runs/.stats.duckdb
                db_path = Path("swarm/runs/.stats.duckdb")
            _global_db = StatsDB(db_path)

            # Trigger connection to perform version check
            _ = _global_db.connection

            # Auto-rebuild if needed
            if auto_rebuild and _global_db.needs_rebuild:
                logger.info("Projection version mismatch detected, rebuilding from events.jsonl...")
                stats = _global_db.rebuild_all_from_events()
                logger.info(
                    "Auto-rebuild complete: %d runs, %d events",
                    stats.get("runs_succeeded", 0),
                    stats.get("events_ingested", 0),
                )

        return _global_db


def close_stats_db() -> None:
    """Close the global StatsDB instance."""
    global _global_db

    with _global_db_lock:
        if _global_db is not None:
            _global_db.close()
            _global_db = None
