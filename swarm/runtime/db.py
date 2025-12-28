"""
db.py - DuckDB-based stats and telemetry storage for Flow Studio.

This module provides a high-performance local database for storing:
- Run metadata and status
- Step execution telemetry
- Tool call statistics
- File change tracking

Design Philosophy:
    - The orchestrator writes to events.jsonl (append-only, crash-safe)
    - This module mirrors events.jsonl into DuckDB for fast queries
    - TypeScript UI queries DuckDB via a small API, not JSONL parsing
    - DuckDB is ephemeral/rebuildable from events.jsonl if needed

Usage:
    from swarm.runtime.db import StatsDB

    db = StatsDB(db_path)
    db.record_step_start(run_id, flow_key, step_id, agent_key)
    db.record_tool_call(run_id, step_id, tool_name, duration_ms, success)
    db.record_step_end(run_id, step_id, status, tokens, routing_signal)

    # Query for UI
    stats = db.get_run_stats(run_id)
    tool_breakdown = db.get_tool_breakdown(run_id)
"""

from __future__ import annotations

import json
import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency at module load time
_duckdb = None


def _get_duckdb():
    """Lazy import of duckdb module."""
    global _duckdb
    if _duckdb is None:
        try:
            import duckdb
            _duckdb = duckdb
        except ImportError:
            logger.warning("DuckDB not available - stats will not be persisted")
            return None
    return _duckdb


# =============================================================================
# Schema Definitions
# =============================================================================

SCHEMA_VERSION = 1

CREATE_TABLES_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Runs table: one row per run
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR PRIMARY KEY,
    flow_keys VARCHAR[],  -- Array of flow keys executed
    profile_id VARCHAR,
    engine_id VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR,  -- running, succeeded, failed, cancelled
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_duration_ms INTEGER DEFAULT 0,
    metadata JSON
);

-- Steps table: one row per step execution
CREATE SEQUENCE IF NOT EXISTS steps_id_seq;
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY DEFAULT nextval('steps_id_seq'),
    run_id VARCHAR NOT NULL,
    flow_key VARCHAR NOT NULL,
    step_id VARCHAR NOT NULL,
    step_index INTEGER,
    agent_key VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR,  -- running, succeeded, failed, skipped
    duration_ms INTEGER DEFAULT 0,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    handoff_status VARCHAR,  -- VERIFIED, UNVERIFIED, PARTIAL, BLOCKED
    routing_decision VARCHAR,  -- advance, loop, terminate, branch
    routing_next_step VARCHAR,
    routing_confidence FLOAT,
    error_message VARCHAR,
    UNIQUE(run_id, flow_key, step_id, started_at)
);

-- Tool calls table: one row per tool invocation
CREATE SEQUENCE IF NOT EXISTS tool_calls_id_seq;
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY DEFAULT nextval('tool_calls_id_seq'),
    run_id VARCHAR NOT NULL,
    step_id VARCHAR NOT NULL,
    tool_name VARCHAR NOT NULL,
    phase VARCHAR,  -- work, finalization, routing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    target_path VARCHAR,  -- For file operations
    diff_lines_added INTEGER,
    diff_lines_removed INTEGER,
    exit_code INTEGER,  -- For bash operations
    error_message VARCHAR
);

-- File changes table: aggregated file modifications per step
CREATE SEQUENCE IF NOT EXISTS file_changes_id_seq;
CREATE TABLE IF NOT EXISTS file_changes (
    id INTEGER PRIMARY KEY DEFAULT nextval('file_changes_id_seq'),
    run_id VARCHAR NOT NULL,
    step_id VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    change_type VARCHAR,  -- created, modified, deleted
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    timestamp TIMESTAMP,
    UNIQUE(run_id, step_id, file_path)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_steps_run_id ON steps(run_id);
CREATE INDEX IF NOT EXISTS idx_steps_flow_step ON steps(flow_key, step_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_run_id ON tool_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_step_id ON tool_calls(step_id);
CREATE INDEX IF NOT EXISTS idx_file_changes_run_id ON file_changes(run_id);

-- Events table: raw event storage for idempotent ingestion
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR PRIMARY KEY,
    seq INTEGER NOT NULL,
    run_id VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    kind VARCHAR NOT NULL,
    flow_key VARCHAR NOT NULL,
    step_id VARCHAR,
    agent_key VARCHAR,
    payload JSON,
    ingested_at TIMESTAMP DEFAULT (now())
);

CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_run_kind ON events(run_id, kind);

-- Ingestion state table: offset tracking for incremental ingestion
CREATE TABLE IF NOT EXISTS ingestion_state (
    run_id VARCHAR PRIMARY KEY,
    last_offset INTEGER NOT NULL DEFAULT 0,
    last_seq INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT (now())
);
"""


# =============================================================================
# Data Classes for Type Safety
# =============================================================================


@dataclass
class RunStats:
    """Aggregated statistics for a run."""
    run_id: str
    flow_keys: List[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_steps: int
    completed_steps: int
    total_tokens: int
    total_duration_ms: int
    tool_call_count: int = 0
    file_change_count: int = 0


@dataclass
class StepStats:
    """Statistics for a single step."""
    step_id: str
    flow_key: str
    agent_key: Optional[str]
    status: str
    duration_ms: int
    total_tokens: int
    handoff_status: Optional[str]
    routing_decision: Optional[str]
    tool_calls: int = 0


@dataclass
class ToolBreakdown:
    """Breakdown of tool usage."""
    tool_name: str
    call_count: int
    total_duration_ms: int
    success_rate: float
    avg_duration_ms: float


# =============================================================================
# StatsDB Class
# =============================================================================


class StatsDB:
    """DuckDB-backed statistics database for Flow Studio.

    Thread-safe wrapper around DuckDB for recording and querying
    execution statistics. Supports concurrent writes from multiple
    step executions.

    Attributes:
        db_path: Path to the DuckDB database file.
        connection: Active DuckDB connection (lazy initialized).
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the stats database.

        Args:
            db_path: Path to the DuckDB file. If None, uses in-memory database.
        """
        self.db_path = db_path
        self._connection = None
        self._lock = threading.RLock()
        self._initialized = False

    @property
    def connection(self):
        """Get or create the DuckDB connection."""
        if self._connection is None:
            duckdb = _get_duckdb()
            if duckdb is None:
                return None

            with self._lock:
                if self._connection is None:
                    if self.db_path:
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
                    "INSERT INTO schema_version (version) VALUES (?)",
                    [SCHEMA_VERSION]
                )

            logger.debug("StatsDB schema initialized (version %d)", SCHEMA_VERSION)

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

    # =========================================================================
    # Raw Event Storage (Idempotent)
    # =========================================================================

    def _insert_raw_event(self, event: Dict[str, Any]) -> bool:
        """Insert raw event if not already present. Returns True if inserted."""
        try:
            # Use RETURNING to detect if insert happened (empty result = conflict/no insert)
            result = self.connection.execute("""
                INSERT INTO events (event_id, seq, run_id, ts, kind, flow_key, step_id, agent_key, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id
            """, [
                event.get("event_id"),
                event.get("seq", 0),
                event["run_id"],
                event["ts"],
                event["kind"],
                event["flow_key"],
                event.get("step_id"),
                event.get("agent_key"),
                json.dumps(event.get("payload", {}))
            ])
            return len(result.fetchall()) > 0
        except Exception as e:
            logger.warning(f"Failed to insert event {event.get('event_id')}: {e}")
            return False

    def get_ingestion_offset(self, run_id: str) -> Tuple[int, int]:
        """Get (byte_offset, last_seq) for incremental ingestion."""
        if self.connection is None:
            return (0, 0)

        with self._lock:
            result = self.connection.execute(
                "SELECT last_offset, last_seq FROM ingestion_state WHERE run_id = ?",
                [run_id]
            ).fetchone()
            return (result[0], result[1]) if result else (0, 0)

    def set_ingestion_offset(self, run_id: str, offset: int, seq: int) -> None:
        """Update ingestion offset after successful tail."""
        if self.connection is None:
            return

        with self._lock:
            self.connection.execute("""
                INSERT INTO ingestion_state (run_id, last_offset, last_seq, updated_at)
                VALUES (?, ?, ?, now())
                ON CONFLICT (run_id) DO UPDATE SET
                    last_offset = excluded.last_offset,
                    last_seq = excluded.last_seq,
                    updated_at = excluded.updated_at
            """, [run_id, offset, seq])

    # =========================================================================
    # Write Operations
    # =========================================================================

    def record_run_start(
        self,
        run_id: str,
        flow_keys: List[str],
        profile_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record the start of a new run."""
        if self.connection is None:
            return

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, flow_keys, profile_id, engine_id, started_at, status, metadata)
                VALUES (?, ?, ?, ?, ?, 'running', ?)
                ON CONFLICT (run_id) DO UPDATE SET
                    flow_keys = EXCLUDED.flow_keys,
                    started_at = EXCLUDED.started_at,
                    status = 'running'
                """,
                [run_id, flow_keys, profile_id, engine_id,
                 datetime.now(timezone.utc), json.dumps(metadata or {})]
            )

    def record_run_end(
        self,
        run_id: str,
        status: str,
        total_steps: int,
        completed_steps: int,
        total_tokens: int,
        total_duration_ms: int,
    ):
        """Record the completion of a run."""
        if self.connection is None:
            return

        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE runs SET
                    completed_at = ?,
                    status = ?,
                    total_steps = ?,
                    completed_steps = ?,
                    total_tokens = ?,
                    total_duration_ms = ?
                WHERE run_id = ?
                """,
                [datetime.now(timezone.utc), status, total_steps, completed_steps,
                 total_tokens, total_duration_ms, run_id]
            )

    def record_step_start(
        self,
        run_id: str,
        flow_key: str,
        step_id: str,
        step_index: int,
        agent_key: Optional[str] = None,
    ):
        """Record the start of a step execution."""
        if self.connection is None:
            return

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO steps (run_id, flow_key, step_id, step_index, agent_key, started_at, status)
                VALUES (?, ?, ?, ?, ?, ?, 'running')
                """,
                [run_id, flow_key, step_id, step_index, agent_key, datetime.now(timezone.utc)]
            )

    def record_step_end(
        self,
        run_id: str,
        flow_key: str,
        step_id: str,
        status: str,
        duration_ms: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        handoff_status: Optional[str] = None,
        routing_decision: Optional[str] = None,
        routing_next_step: Optional[str] = None,
        routing_confidence: Optional[float] = None,
        error_message: Optional[str] = None,
    ):
        """Record the completion of a step execution."""
        if self.connection is None:
            return

        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE steps SET
                    completed_at = ?,
                    status = ?,
                    duration_ms = ?,
                    prompt_tokens = ?,
                    completion_tokens = ?,
                    total_tokens = ?,
                    handoff_status = ?,
                    routing_decision = ?,
                    routing_next_step = ?,
                    routing_confidence = ?,
                    error_message = ?
                WHERE run_id = ? AND flow_key = ? AND step_id = ? AND status = 'running'
                """,
                [datetime.now(timezone.utc), status, duration_ms,
                 prompt_tokens, completion_tokens, prompt_tokens + completion_tokens,
                 handoff_status, routing_decision, routing_next_step, routing_confidence,
                 error_message, run_id, flow_key, step_id]
            )

    def record_tool_call(
        self,
        run_id: str,
        step_id: str,
        tool_name: str,
        phase: str = "work",
        duration_ms: int = 0,
        success: bool = True,
        target_path: Optional[str] = None,
        diff_lines_added: Optional[int] = None,
        diff_lines_removed: Optional[int] = None,
        exit_code: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Record a tool call."""
        if self.connection is None:
            return

        now = datetime.now(timezone.utc)
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO tool_calls (
                    run_id, step_id, tool_name, phase, started_at, completed_at,
                    duration_ms, success, target_path, diff_lines_added, diff_lines_removed,
                    exit_code, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [run_id, step_id, tool_name, phase, now, now,
                 duration_ms, success, target_path, diff_lines_added, diff_lines_removed,
                 exit_code, error_message]
            )

    def record_file_change(
        self,
        run_id: str,
        step_id: str,
        file_path: str,
        change_type: str,
        lines_added: int = 0,
        lines_removed: int = 0,
    ):
        """Record a file change."""
        if self.connection is None:
            return

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO file_changes (run_id, step_id, file_path, change_type, lines_added, lines_removed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (run_id, step_id, file_path) DO UPDATE SET
                    change_type = EXCLUDED.change_type,
                    lines_added = file_changes.lines_added + EXCLUDED.lines_added,
                    lines_removed = file_changes.lines_removed + EXCLUDED.lines_removed
                """,
                [run_id, step_id, file_path, change_type, lines_added, lines_removed,
                 datetime.now(timezone.utc)]
            )

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def ingest_events(self, events: List[Dict[str, Any]], run_id: str) -> int:
        """Batch ingest events from events.jsonl format (idempotent).

        This is the primary interface for the event sink pattern.
        First inserts raw events into the events table (dedup by event_id),
        then updates projections (runs, steps, tool_calls, file_changes).

        Args:
            events: List of event dicts (from events.jsonl).
            run_id: The run ID these events belong to.

        Returns:
            Number of newly ingested events (events that were not already present).
        """
        if self.connection is None:
            return 0

        newly_ingested = 0

        for event in events:
            # Ensure run_id is set on the event for raw storage
            event_with_run = {**event, "run_id": run_id}

            # Insert raw event first (idempotent - skips if event_id exists)
            if not self._insert_raw_event(event_with_run):
                # Event already exists, skip projection updates
                continue

            newly_ingested += 1

            # Update projections for new events
            kind = event.get("kind", "")
            payload = event.get("payload", {})
            step_id = event.get("step_id", "")
            flow_key = event.get("flow_key", "")

            if kind == "step_start":
                self.record_step_start(
                    run_id=run_id,
                    flow_key=flow_key,
                    step_id=step_id,
                    step_index=payload.get("step_index", 0),
                    agent_key=payload.get("agent_key"),
                )

            elif kind == "step_complete":
                self.record_step_end(
                    run_id=run_id,
                    flow_key=flow_key,
                    step_id=step_id,
                    status=payload.get("status", "succeeded"),
                    duration_ms=payload.get("duration_ms", 0),
                    prompt_tokens=payload.get("prompt_tokens", 0),
                    completion_tokens=payload.get("completion_tokens", 0),
                    handoff_status=payload.get("handoff_status"),
                    routing_decision=payload.get("routing_decision"),
                    routing_next_step=payload.get("routing_next_step"),
                    routing_confidence=payload.get("routing_confidence"),
                    error_message=payload.get("error"),
                )

            elif kind == "tool_start":
                # We'll update on tool_end
                pass

            elif kind == "tool_end":
                self.record_tool_call(
                    run_id=run_id,
                    step_id=step_id,
                    tool_name=payload.get("tool", "unknown"),
                    phase=payload.get("phase", "work"),
                    duration_ms=payload.get("duration_ms", 0),
                    success=payload.get("success", True),
                    target_path=payload.get("target_path"),
                    diff_lines_added=payload.get("diff_lines_added"),
                    diff_lines_removed=payload.get("diff_lines_removed"),
                    exit_code=payload.get("exit_code"),
                    error_message=payload.get("error"),
                )

            elif kind == "file_changes":
                # File changes from DiffScanner (forensic truth)
                files = payload.get("files", [])
                for fc in files:
                    self.record_file_change(
                        run_id=run_id,
                        step_id=step_id,
                        file_path=fc.get("path", ""),
                        change_type=fc.get("status", "modified"),
                        lines_added=fc.get("insertions", 0),
                        lines_removed=fc.get("deletions", 0),
                    )

            elif kind == "run_start":
                # Run initialization
                flow_keys = payload.get("flow_keys", [])
                self.record_run_start(
                    run_id=run_id,
                    flow_keys=flow_keys,
                    profile_id=payload.get("profile_id"),
                    engine_id=payload.get("engine"),
                    metadata=payload.get("metadata"),
                )

            elif kind == "run_completed":
                # Run completion
                self.record_run_end(
                    run_id=run_id,
                    status=payload.get("status", "completed"),
                    total_steps=payload.get("total_steps", 0),
                    completed_steps=payload.get("steps_completed", 0),
                    total_tokens=payload.get("total_tokens", 0),
                    total_duration_ms=payload.get("duration_ms", 0),
                )

        return newly_ingested

    # =========================================================================
    # Query Operations (for TypeScript UI)
    # =========================================================================

    def get_run_stats(self, run_id: str) -> Optional[RunStats]:
        """Get aggregated statistics for a run."""
        if self.connection is None:
            return None

        with self._lock:
            result = self.connection.execute(
                """
                SELECT
                    r.run_id,
                    r.flow_keys,
                    r.status,
                    r.started_at,
                    r.completed_at,
                    r.total_steps,
                    r.completed_steps,
                    r.total_tokens,
                    r.total_duration_ms,
                    (SELECT COUNT(*) FROM tool_calls WHERE run_id = r.run_id) as tool_call_count,
                    (SELECT COUNT(*) FROM file_changes WHERE run_id = r.run_id) as file_change_count
                FROM runs r
                WHERE r.run_id = ?
                """,
                [run_id]
            ).fetchone()

            if result is None:
                return None

            return RunStats(
                run_id=result[0],
                flow_keys=result[1] or [],
                status=result[2],
                started_at=result[3],
                completed_at=result[4],
                total_steps=result[5] or 0,
                completed_steps=result[6] or 0,
                total_tokens=result[7] or 0,
                total_duration_ms=result[8] or 0,
                tool_call_count=result[9] or 0,
                file_change_count=result[10] or 0,
            )

    def get_step_stats(self, run_id: str) -> List[StepStats]:
        """Get statistics for all steps in a run."""
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    s.step_id,
                    s.flow_key,
                    s.agent_key,
                    s.status,
                    s.duration_ms,
                    s.total_tokens,
                    s.handoff_status,
                    s.routing_decision,
                    (SELECT COUNT(*) FROM tool_calls WHERE run_id = s.run_id AND step_id = s.step_id) as tool_calls
                FROM steps s
                WHERE s.run_id = ?
                ORDER BY s.step_index
                """,
                [run_id]
            ).fetchall()

            return [
                StepStats(
                    step_id=row[0],
                    flow_key=row[1],
                    agent_key=row[2],
                    status=row[3],
                    duration_ms=row[4] or 0,
                    total_tokens=row[5] or 0,
                    handoff_status=row[6],
                    routing_decision=row[7],
                    tool_calls=row[8] or 0,
                )
                for row in results
            ]

    def get_tool_breakdown(self, run_id: str) -> List[ToolBreakdown]:
        """Get breakdown of tool usage for a run."""
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    tool_name,
                    COUNT(*) as call_count,
                    SUM(duration_ms) as total_duration_ms,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(duration_ms) as avg_duration_ms
                FROM tool_calls
                WHERE run_id = ?
                GROUP BY tool_name
                ORDER BY call_count DESC
                """,
                [run_id]
            ).fetchall()

            return [
                ToolBreakdown(
                    tool_name=row[0],
                    call_count=row[1],
                    total_duration_ms=row[2] or 0,
                    success_rate=row[3] or 1.0,
                    avg_duration_ms=row[4] or 0.0,
                )
                for row in results
            ]

    def get_recent_runs(self, limit: int = 20) -> List[RunStats]:
        """Get recent runs for the UI dashboard."""
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    r.run_id,
                    r.flow_keys,
                    r.status,
                    r.started_at,
                    r.completed_at,
                    r.total_steps,
                    r.completed_steps,
                    r.total_tokens,
                    r.total_duration_ms,
                    (SELECT COUNT(*) FROM tool_calls WHERE run_id = r.run_id) as tool_call_count,
                    (SELECT COUNT(*) FROM file_changes WHERE run_id = r.run_id) as file_change_count
                FROM runs r
                ORDER BY r.started_at DESC
                LIMIT ?
                """,
                [limit]
            ).fetchall()

            return [
                RunStats(
                    run_id=row[0],
                    flow_keys=row[1] or [],
                    status=row[2],
                    started_at=row[3],
                    completed_at=row[4],
                    total_steps=row[5] or 0,
                    completed_steps=row[6] or 0,
                    total_tokens=row[7] or 0,
                    total_duration_ms=row[8] or 0,
                    tool_call_count=row[9] or 0,
                    file_change_count=row[10] or 0,
                )
                for row in results
            ]

    def get_file_changes(self, run_id: str) -> List[Dict[str, Any]]:
        """Get file changes for a run."""
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT file_path, change_type, lines_added, lines_removed, step_id, timestamp
                FROM file_changes
                WHERE run_id = ?
                ORDER BY timestamp
                """,
                [run_id]
            ).fetchall()

            return [
                {
                    "file_path": row[0],
                    "change_type": row[1],
                    "lines_added": row[2],
                    "lines_removed": row[3],
                    "step_id": row[4],
                    "timestamp": row[5].isoformat() if row[5] else None,
                }
                for row in results
            ]


# =============================================================================
# Global Instance (Singleton Pattern)
# =============================================================================

_global_db: Optional[StatsDB] = None
_global_db_lock = threading.Lock()


def get_stats_db(db_path: Optional[Path] = None) -> StatsDB:
    """Get the global StatsDB instance.

    Creates a new instance if one doesn't exist, or if a different
    db_path is requested.

    Args:
        db_path: Path to the DuckDB file. If None, uses default location.

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

        return _global_db


def close_stats_db():
    """Close the global StatsDB instance."""
    global _global_db

    with _global_db_lock:
        if _global_db is not None:
            _global_db.close()
            _global_db = None


# =============================================================================
# Disk-as-Truth Recovery: Rebuild DuckDB from events.jsonl
# =============================================================================


def rebuild_stats_db(
    runs_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
    run_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Rebuild the DuckDB stats database from disk artifacts.

    This function implements the "disk-as-truth" principle:
    - events.jsonl is the append-only journal (durable, crash-safe)
    - DuckDB is a projection that can be rebuilt at any time

    The rebuild process:
    1. Scan runs_dir for run directories (or use provided run_ids)
    2. For each run, read events.jsonl
    3. Parse events and call ingest_events to populate DuckDB
    4. Read handoff envelopes for additional routing/status data

    Args:
        runs_dir: Path to the runs directory. Defaults to swarm/runs/.
        db_path: Path to the DuckDB file. If None, uses default.
        run_ids: Optional list of specific run IDs to rebuild.
                 If None, rebuilds all runs found in runs_dir.

    Returns:
        Dict with rebuild statistics:
        - runs_processed: Number of runs processed
        - events_ingested: Total events ingested
        - errors: List of any errors encountered
    """
    from . import storage as storage_module

    if runs_dir is None:
        runs_dir = storage_module.RUNS_DIR

    if db_path is None:
        db_path = runs_dir / ".stats.duckdb"

    # Create fresh database (drop existing)
    if db_path.exists():
        logger.info("Removing existing stats database: %s", db_path)
        db_path.unlink()

    db = StatsDB(db_path)

    stats = {
        "runs_processed": 0,
        "events_ingested": 0,
        "envelopes_processed": 0,
        "errors": [],
    }

    # Get list of run IDs to process
    if run_ids is None:
        # Scan runs directory
        if not runs_dir.exists():
            logger.warning("Runs directory does not exist: %s", runs_dir)
            return stats

        run_ids = [
            d.name for d in runs_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    logger.info("Rebuilding stats DB from %d runs", len(run_ids))

    for run_id in run_ids:
        try:
            run_path = runs_dir / run_id
            events_file = run_path / storage_module.EVENTS_FILE

            if not events_file.exists():
                logger.debug("No events.jsonl for run %s, skipping", run_id)
                continue

            # Read and parse events
            events: List[Dict[str, Any]] = []
            with events_file.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError as e:
                        stats["errors"].append({
                            "run_id": run_id,
                            "file": "events.jsonl",
                            "line": line_num,
                            "error": str(e),
                        })

            if events:
                # Ingest events into DuckDB
                db.ingest_events(events, run_id)
                stats["events_ingested"] += len(events)

            # Also process handoff envelopes for routing info
            for flow_dir in run_path.iterdir():
                if not flow_dir.is_dir() or flow_dir.name.startswith("."):
                    continue

                handoff_dir = flow_dir / "handoff"
                if not handoff_dir.exists():
                    continue

                for envelope_file in handoff_dir.glob("*.json"):
                    try:
                        with envelope_file.open("r", encoding="utf-8") as f:
                            envelope_data = json.load(f)

                        # Record file changes from envelope if present
                        file_changes = envelope_data.get("file_changes", {})
                        if file_changes and "files" in file_changes:
                            step_id = envelope_data.get("step_id", envelope_file.stem)
                            for fc in file_changes.get("files", []):
                                db.record_file_change(
                                    run_id=run_id,
                                    step_id=step_id,
                                    file_path=fc.get("path", ""),
                                    change_type=fc.get("status", "modified"),
                                    lines_added=fc.get("insertions", 0),
                                    lines_removed=fc.get("deletions", 0),
                                )

                        stats["envelopes_processed"] += 1

                    except (json.JSONDecodeError, IOError) as e:
                        stats["errors"].append({
                            "run_id": run_id,
                            "file": str(envelope_file),
                            "error": str(e),
                        })

            stats["runs_processed"] += 1

        except Exception as e:
            logger.warning("Error processing run %s: %s", run_id, e)
            stats["errors"].append({
                "run_id": run_id,
                "error": str(e),
            })

    db.close()

    logger.info(
        "Rebuild complete: %d runs, %d events, %d envelopes, %d errors",
        stats["runs_processed"],
        stats["events_ingested"],
        stats["envelopes_processed"],
        len(stats["errors"]),
    )

    return stats


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """CLI entry point for stats database operations.

    Usage:
        python -m swarm.runtime.db rebuild [--runs-dir PATH] [--db-path PATH]
        python -m swarm.runtime.db stats <run_id>
    """
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Flow Studio Stats Database CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Rebuild command
    rebuild_parser = subparsers.add_parser(
        "rebuild",
        help="Rebuild DuckDB from events.jsonl (disk-as-truth)",
    )
    rebuild_parser.add_argument(
        "--runs-dir",
        type=Path,
        default=None,
        help="Path to runs directory (default: swarm/runs/)",
    )
    rebuild_parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to DuckDB file (default: <runs-dir>/.stats.duckdb)",
    )
    rebuild_parser.add_argument(
        "--run-id",
        action="append",
        dest="run_ids",
        help="Specific run ID to rebuild (can be repeated)",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show statistics for a run",
    )
    stats_parser.add_argument("run_id", help="Run ID to query")

    args = parser.parse_args()

    if args.command == "rebuild":
        print("Rebuilding stats database...")
        result = rebuild_stats_db(
            runs_dir=args.runs_dir,
            db_path=args.db_path,
            run_ids=args.run_ids,
        )
        print(f"\nRebuild complete:")
        print(f"  Runs processed: {result['runs_processed']}")
        print(f"  Events ingested: {result['events_ingested']}")
        print(f"  Envelopes processed: {result['envelopes_processed']}")
        if result["errors"]:
            print(f"  Errors: {len(result['errors'])}")
            for err in result["errors"][:5]:
                print(f"    - {err}")
        sys.exit(0)

    elif args.command == "stats":
        db = get_stats_db()
        run_stats = db.get_run_stats(args.run_id)
        if run_stats is None:
            print(f"Run not found: {args.run_id}")
            sys.exit(1)

        print(f"Run: {run_stats.run_id}")
        print(f"  Status: {run_stats.status}")
        print(f"  Flows: {', '.join(run_stats.flow_keys)}")
        print(f"  Steps: {run_stats.completed_steps}/{run_stats.total_steps}")
        print(f"  Tokens: {run_stats.total_tokens}")
        print(f"  Duration: {run_stats.total_duration_ms}ms")
        print(f"  Tool calls: {run_stats.tool_call_count}")
        print(f"  File changes: {run_stats.file_change_count}")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
