from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.runtime.safe_paths import validate_path_component

logger = logging.getLogger(__name__)


class StatsDBRebuildMixin:
    def rebuild_from_events(
        self,
        run_id: str,
        runs_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Rebuild projection for a single run from its events.jsonl.

        This method re-ingests all events from a run's events.jsonl file
        into the DuckDB projection tables. It's used when:
        - Projection version mismatch is detected
        - User requests a rebuild
        - Recovering from corruption

        The events.jsonl is the authoritative ledger; DuckDB is disposable.

        Args:
            run_id: The run ID to rebuild.
            runs_dir: Base directory for runs. Defaults to RUNS_DIR from storage.

        Returns:
            Dict with rebuild statistics:
            - events_ingested: Number of events processed
            - success: True if rebuild completed
            - error: Error message if failed
        """
        from .. import storage as storage_module

        # Security check: Prevent path traversal
        validate_path_component(run_id, "run_id")

        if runs_dir is None:
            runs_dir = storage_module.RUNS_DIR

        result = {
            "run_id": run_id,
            "events_ingested": 0,
            "success": False,
            "error": None,
        }

        run_path = runs_dir / run_id
        events_file = run_path / storage_module.EVENTS_FILE

        if not events_file.exists():
            # No events file is fine - empty projection
            logger.debug("No events.jsonl for run %s, projection will be empty", run_id)
            result["success"] = True
            return result

        try:
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
                        logger.warning(
                            "Skipping malformed event at line %d in %s: %s",
                            line_num,
                            events_file,
                            e,
                        )

            if events:
                # Ingest events into DuckDB (idempotent)
                count = self.ingest_events(events, run_id)
                result["events_ingested"] = count
                logger.info("Rebuilt projection for run %s: %d events ingested", run_id, count)

            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            logger.warning("Failed to rebuild projection for run %s: %s", run_id, e)

        return result

    def rebuild_all_from_events(
        self,
        runs_dir: Optional[Path] = None,
        run_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Rebuild projections for all runs from their events.jsonl files.

        This method scans the runs directory and rebuilds projections for
        each run that has an events.jsonl file. Use this after a projection
        version bump to repopulate the entire database.

        Args:
            runs_dir: Base directory for runs. Defaults to RUNS_DIR from storage.
            run_ids: Optional list of specific run IDs to rebuild.
                     If None, rebuilds all runs found in runs_dir.

        Returns:
            Dict with rebuild statistics:
            - runs_processed: Number of runs processed
            - runs_succeeded: Number of runs successfully rebuilt
            - events_ingested: Total events ingested
            - errors: List of any errors encountered
        """
        from .. import storage as storage_module

        if runs_dir is None:
            runs_dir = storage_module.RUNS_DIR

        stats = {
            "runs_processed": 0,
            "runs_succeeded": 0,
            "events_ingested": 0,
            "errors": [],
        }

        # Get list of run IDs to process
        if run_ids is None:
            if not runs_dir.exists():
                logger.warning("Runs directory does not exist: %s", runs_dir)
                return stats

            run_ids = [
                d.name for d in runs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]

        logger.info("Rebuilding projections for %d runs", len(run_ids))

        for run_id in run_ids:
            result = self.rebuild_from_events(run_id, runs_dir)
            stats["runs_processed"] += 1

            if result["success"]:
                stats["runs_succeeded"] += 1
                stats["events_ingested"] += result["events_ingested"]
            else:
                stats["errors"].append(
                    {
                        "run_id": run_id,
                        "error": result.get("error", "Unknown error"),
                    }
                )

        logger.info(
            "Rebuild complete: %d/%d runs, %d events, %d errors",
            stats["runs_succeeded"],
            stats["runs_processed"],
            stats["events_ingested"],
            len(stats["errors"]),
        )

        # Clear the needs_rebuild flag after successful rebuild
        self._needs_rebuild = False

        return stats

    @property
    def needs_rebuild(self) -> bool:
        """Check if the database needs to be rebuilt from events.jsonl.

        This is set to True when:
        - Projection version mismatch is detected
        - Database was missing and freshly created

        After calling rebuild_all_from_events(), this is set to False.
        """
        return self._needs_rebuild


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
    from .. import storage as storage_module
    from .db import StatsDB
    from .ingestion import _ingestion_context

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

        run_ids = [d.name for d in runs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    logger.info("Rebuilding stats DB from %d runs", len(run_ids))

    for run_id in run_ids:
        try:
            validate_path_component(run_id, "run_id")
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
                        stats["errors"].append(
                            {
                                "run_id": run_id,
                                "file": "events.jsonl",
                                "line": line_num,
                                "error": str(e),
                            }
                        )

            if events:
                # Ingest events into DuckDB
                db.ingest_events(events, run_id)
                stats["events_ingested"] += len(events)

            # Also process handoff envelopes for routing info
            # Set ingestion context to allow record_* calls (projection-only mode)
            _ingestion_context.active = True
            try:
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
                            stats["errors"].append(
                                {
                                    "run_id": run_id,
                                    "file": str(envelope_file),
                                    "error": str(e),
                                }
                            )
            finally:
                _ingestion_context.active = False

            stats["runs_processed"] += 1

        except Exception as e:
            logger.warning("Error processing run %s: %s", run_id, e)
            stats["errors"].append(
                {
                    "run_id": run_id,
                    "error": str(e),
                }
            )

    db.close()

    logger.info(
        "Rebuild complete: %d runs, %d events, %d envelopes, %d errors",
        stats["runs_processed"],
        stats["events_ingested"],
        stats["envelopes_processed"],
        len(stats["errors"]),
    )

    return stats
