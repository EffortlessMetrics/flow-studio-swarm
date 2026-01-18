from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .rebuild import rebuild_stats_db
from .singleton import get_stats_db


def main() -> None:
    """CLI entry point for stats database operations.

    Usage:
        python -m swarm.runtime.db rebuild [--runs-dir PATH] [--db-path PATH]
        python -m swarm.runtime.db stats <run_id>
        python -m swarm.runtime.db doctor <run_id> [--strict] [--from-disk]
    """
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

    # Doctor command (event contract validation)
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Validate event stream contract for a run",
    )
    doctor_parser.add_argument("run_id", help="Run ID to validate")
    doctor_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    doctor_parser.add_argument(
        "--from-disk",
        action="store_true",
        help="Read events from disk (events.jsonl) instead of DB",
    )
    doctor_parser.add_argument(
        "--runs-dir",
        type=Path,
        default=None,
        help="Path to runs directory (for --from-disk mode)",
    )

    args = parser.parse_args()

    if args.command == "rebuild":
        print("Rebuilding stats database...")
        result = rebuild_stats_db(
            runs_dir=args.runs_dir,
            db_path=args.db_path,
            run_ids=args.run_ids,
        )
        print("\nRebuild complete:")
        print(f"  Runs processed: {result['runs_processed']}")
        print(f"  Events ingested: {result['events_ingested']}")
        print(f"  Envelopes processed: {result['envelopes_processed']}")
        if result["errors"]:
            print(f"  Errors: {len(result['errors'])}")
            for err in result["errors"][:5]:
                print(f"    - {err}")
        sys.exit(0)

    if args.command == "stats":
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

    if args.command == "doctor":
        from ..event_validator import (
            format_violations,
            validate_run_from_db,
            validate_run_from_disk,
        )
        from ..storage import RUNS_DIR

        runs_dir = args.runs_dir or RUNS_DIR

        if args.from_disk:
            violations = validate_run_from_disk(args.run_id, runs_dir, strict=args.strict)
        else:
            db = get_stats_db()
            violations = validate_run_from_db(args.run_id, db, strict=args.strict)

        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]

        if not violations:
            print(f"Run {args.run_id}: event stream valid")
            sys.exit(0)

        print(f"Run {args.run_id}: {len(errors)} error(s), {len(warnings)} warning(s)")
        print(format_violations(violations))

        # Exit with error code if there are errors
        sys.exit(1 if errors else 0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
