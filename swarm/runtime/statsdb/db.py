from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from .duckdb_import import _get_duckdb
from .ingestion import StatsDBIngestionMixin, _is_in_ingestion_context
from .queries import StatsDBQueryMixin
from .rebuild import StatsDBRebuildMixin
from .schema_sql import CREATE_TABLES_SQL
from .versions import (
    PROJECTION_VERSION,
    SCHEMA_VERSION,
    _check_projection_version,
    _set_projection_version,
)

logger = logging.getLogger(__name__)


class StatsDB(StatsDBIngestionMixin, StatsDBQueryMixin, StatsDBRebuildMixin):
    """DuckDB-backed statistics database for Flow Studio.

    Thread-safe wrapper around DuckDB for recording and querying
    execution statistics. Supports concurrent writes from multiple
    step executions.

    Attributes:
        db_path: Path to the DuckDB database file.
        connection: Active DuckDB connection (lazy initialized).
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        projection_only: Optional[bool] = None,
        projection_strict: Optional[bool] = None,
    ):
        """Initialize the stats database.

        Args:
            db_path: Path to the DuckDB file. If None, uses in-memory database.
            projection_only: If True, direct record_* calls are no-ops.
                Defaults to SWARM_DB_PROJECTION_ONLY env var (default: true).
            projection_strict: If True, direct record_* calls raise RuntimeError.
                Defaults to SWARM_DB_PROJECTION_STRICT env var (default: false).
        """
        self.db_path = db_path
        self._connection = None
        self._lock = threading.RLock()
        self._initialized = False
        self._version_checked = False
        self._needs_rebuild = False

        # Capture projection config at construction time (not import time)
        # This allows tests to set env vars after import but before construction
        if projection_only is None:
            projection_only = os.environ.get("SWARM_DB_PROJECTION_ONLY", "true").lower() == "true"
        if projection_strict is None:
            projection_strict = (
                os.environ.get("SWARM_DB_PROJECTION_STRICT", "false").lower() == "true"
            )

        self._projection_only = projection_only
        self._projection_strict = projection_strict

    def _projection_guard(self, method_name: str) -> bool:
        """Check if direct projection writes are allowed.

        In projection-only mode, direct record_* calls are skipped (or raise in
        strict mode). This ensures all DB state comes from event ingestion.

        Calls from within ingest_events() are always allowed.

        Args:
            method_name: Name of the calling method for logging.

        Returns:
            True if write should proceed, False if should be skipped.

        Raises:
            RuntimeError: In strict mode when direct writes are attempted.
        """
        # Always allow calls from ingestion context
        if _is_in_ingestion_context():
            return True

        if not self._projection_only:
            return True  # Legacy mode, allow direct writes

        if self._projection_strict:
            raise RuntimeError(
                f"Direct DB write via {method_name}() blocked in projection-only mode. "
                "Use event emission + ingest_events() instead. "
                "Set SWARM_DB_PROJECTION_ONLY=false to disable this check."
            )

        logger.debug("Projection-only mode: skipping direct %s() call", method_name)
        return False

    @property
    def connection(self):
        """Get or create the DuckDB connection.

        On first access, performs projection version check. If the stored version
        doesn't match PROJECTION_VERSION, the old DB is renamed and a fresh one
        is created. The _needs_rebuild flag is set to signal that the caller
        should rebuild from events.jsonl.
        """
        if self._connection is None:
            duckdb = _get_duckdb()
            if duckdb is None:
                return None

            with self._lock:
                if self._connection is None:
                    if self.db_path:
                        # Check projection version before connecting
                        if not self._version_checked:
                            self._version_checked = True
                            is_compatible = _check_projection_version(self.db_path)
                            if not is_compatible:
                                self._needs_rebuild = True
                                logger.info(
                                    "Projection version mismatch or missing DB. "
                                    "Will rebuild from events.jsonl."
                                )

                        self.db_path.parent.mkdir(parents=True, exist_ok=True)
                        self._connection = duckdb.connect(str(self.db_path))
                    else:
                        self._connection = duckdb.connect(":memory:")

                    if not self._initialized:
                        self._init_schema()
                        self._initialized = True

        return self._connection

    def _init_schema(self):
        """Initialize the database schema."""
        if self.connection is None:
            return

        with self._lock:
            self.connection.execute(CREATE_TABLES_SQL)

            # Check/set schema version
            result = self.connection.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ).fetchone()

            if result is None:
                self.connection.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", [SCHEMA_VERSION]
                )

            # Set projection version (for schema resilience)
            _set_projection_version(self.connection, PROJECTION_VERSION)

            logger.debug(
                "StatsDB schema initialized (schema_version=%d, projection_version=%d)",
                SCHEMA_VERSION,
                PROJECTION_VERSION,
            )

    @contextmanager
    def _transaction(self) -> Iterator[Any]:
        """Context manager for database operations.

        DuckDB auto-commits by default, so we just need locking for thread safety.
        """
        if self.connection is None:
            yield None
            return

        with self._lock:
            try:
                yield self.connection
            except Exception as e:
                logger.warning("Database operation failed: %s", e)
                raise

    def close(self):
        """Close the database connection."""
        if self._connection is not None:
            with self._lock:
                self._connection.close()
                self._connection = None
