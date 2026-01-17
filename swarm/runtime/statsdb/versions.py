from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from .duckdb_import import _get_duckdb

logger = logging.getLogger(__name__)

# =============================================================================
# Schema Versions
# =============================================================================

SCHEMA_VERSION = 2

# =============================================================================
# Projection Version (Schema Resilience)
# =============================================================================
# The projection version tracks breaking changes to the DuckDB projection layer.
# Unlike SCHEMA_VERSION (which is stored in the DB and used for migrations),
# PROJECTION_VERSION is used to detect when a full rebuild from events.jsonl
# is required.
#
# Increment this when:
# - Adding new tables that need data from existing events
# - Changing column types in ways that require re-ingestion
# - Modifying how events are projected into tables
#
# DO NOT increment for:
# - Adding new indexes (additive, non-breaking)
# - Adding nullable columns with defaults (additive, non-breaking)
#
# When PROJECTION_VERSION mismatches the stored version in _projection_meta:
# 1. The old DB file is renamed to stats.db.old.<timestamp>
# 2. A fresh DB is created with the new version
# 3. Data is rebuilt from events.jsonl (empty projection if no events exist)

PROJECTION_VERSION = 2


def _check_projection_version(db_path: Path) -> bool:
    """Check if the projection version matches and handle mismatch.

    This function implements the schema resilience pattern:
    1. Open the existing DB (if any) and read _projection_meta.projection_version
    2. If version matches PROJECTION_VERSION, return True (DB is compatible)
    3. If version mismatches or DB doesn't exist, rename old DB and return False

    The caller is responsible for rebuilding from events.jsonl when this returns False.

    Args:
        db_path: Path to the DuckDB file.

    Returns:
        True if DB is compatible and can be used as-is.
        False if DB was renamed/missing and needs rebuild.
    """
    duckdb = _get_duckdb()
    if duckdb is None:
        return False

    if not db_path.exists():
        logger.debug("No existing DB at %s, will create fresh", db_path)
        return False

    # Try to read the projection version from existing DB
    try:
        conn = duckdb.connect(str(db_path), read_only=True)
        try:
            # Check if _projection_meta table exists
            result = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = '_projection_meta'"
            ).fetchone()

            if result[0] == 0:
                # Table doesn't exist - old schema, needs rebuild
                logger.info("DB at %s missing _projection_meta table, will rebuild", db_path)
                conn.close()
                _rename_old_db(db_path)
                return False

            # Read version
            result = conn.execute(
                "SELECT value FROM _projection_meta WHERE key = 'projection_version'"
            ).fetchone()

            if result is None:
                logger.info("DB at %s missing projection_version, will rebuild", db_path)
                conn.close()
                _rename_old_db(db_path)
                return False

            stored_version = int(result[0])
            if stored_version != PROJECTION_VERSION:
                logger.info(
                    "Projection version mismatch: DB has v%d, code expects v%d. Rebuilding.",
                    stored_version,
                    PROJECTION_VERSION,
                )
                conn.close()
                _rename_old_db(db_path)
                return False

            # Version matches, DB is compatible
            conn.close()
            return True

        except Exception as e:
            logger.warning("Error reading projection version from %s: %s", db_path, e)
            try:
                conn.close()
            except Exception:
                pass
            _rename_old_db(db_path)
            return False

    except Exception as e:
        logger.warning("Error opening DB at %s: %s", db_path, e)
        _rename_old_db(db_path)
        return False


def _rename_old_db(db_path: Path) -> None:
    """Rename old DB file to stats.db.old.<timestamp>.

    Args:
        db_path: Path to the DuckDB file to rename.
    """
    if not db_path.exists():
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    old_path = db_path.parent / f"{db_path.name}.old.{timestamp}"

    try:
        db_path.rename(old_path)
        logger.info("Renamed old DB to %s", old_path)
    except OSError as e:
        logger.warning("Failed to rename old DB %s: %s", db_path, e)
        # Try to delete if rename failed
        try:
            db_path.unlink()
            logger.info("Deleted old DB at %s", db_path)
        except OSError as e2:
            logger.error("Failed to delete old DB %s: %s", db_path, e2)


def _set_projection_version(conn, version: int) -> None:
    """Store the projection version in _projection_meta.

    Args:
        conn: Active DuckDB connection.
        version: The projection version to store.
    """
    conn.execute(
        """
        INSERT INTO _projection_meta (key, value, updated_at)
        VALUES ('projection_version', ?, now())
        ON CONFLICT (key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
    """,
        [str(version)],
    )
