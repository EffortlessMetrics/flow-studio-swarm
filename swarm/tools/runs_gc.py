#!/usr/bin/env python3
"""Runs garbage collection tool.

Provides commands for managing run lifecycle:
- list: Show run counts, sizes, and statistics
- prune: Apply retention policy to delete old runs
- quarantine: Move corrupt runs to _corrupt/ directory

Usage:
    uv run swarm/tools/runs_gc.py list
    uv run swarm/tools/runs_gc.py prune --keep 200 --days 7
    uv run swarm/tools/runs_gc.py prune --dry-run
    uv run swarm/tools/runs_gc.py quarantine
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swarm.config.runs_retention_config import (
    get_max_count,
    get_preserved_named_runs,
    get_preserved_prefixes,
    get_preserved_tags,
    get_retention_days,
    is_dry_run_enabled,
    is_retention_enabled,
    should_log_deletions,
)
from swarm.runtime.storage import (
    EXAMPLES_DIR,
    META_FILE,
    RUNS_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class RunInfo:
    """Information about a run for GC decisions."""

    run_id: str
    path: Path
    run_type: str  # "active", "example", "legacy"
    size_bytes: int
    mtime: datetime
    has_meta: bool
    is_corrupt: bool
    tags: List[str]

    @property
    def age_days(self) -> float:
        """Age in days since last modification."""
        now = datetime.now(timezone.utc)
        return (now - self.mtime).total_seconds() / 86400


def get_dir_size(path: Path) -> int:
    """Get total size of a directory in bytes."""
    total = 0
    try:
        # Performance optimization: Use os.scandir recursively instead of pathlib.Path.rglob.
        # os.scandir yields lightweight DirEntry objects and caches stat() results,
        # which avoids the overhead of instantiating heavy Path objects and performing
        # redundant system calls. This makes calculating size significantly faster.
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        total += get_dir_size(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def get_run_info(run_id: str, run_path: Path, run_type: str) -> RunInfo:
    """Collect information about a single run."""
    meta_path = run_path / META_FILE
    has_meta = meta_path.exists()
    is_corrupt = False
    tags: List[str] = []

    # Check if metadata is corrupt
    if has_meta:
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tags = data.get("tags", [])
        except (json.JSONDecodeError, OSError):
            is_corrupt = True

    # Get modification time
    try:
        stat = run_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    except OSError:
        mtime = datetime.now(timezone.utc)

    # Get size
    size_bytes = get_dir_size(run_path)

    return RunInfo(
        run_id=run_id,
        path=run_path,
        run_type=run_type,
        size_bytes=size_bytes,
        mtime=mtime,
        has_meta=has_meta,
        is_corrupt=is_corrupt,
        tags=tags,
    )


def discover_all_runs() -> List[RunInfo]:
    """Discover all runs from runs/ and examples/ directories."""
    runs: List[RunInfo] = []
    seen: set[str] = set()

    # Examples (always preserved)
    if EXAMPLES_DIR.exists():
        for entry in EXAMPLES_DIR.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                if entry.name not in seen:
                    seen.add(entry.name)
                    runs.append(get_run_info(entry.name, entry, "example"))

    # Active runs with meta.json
    if RUNS_DIR.exists():
        for entry in RUNS_DIR.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                if entry.name in seen:
                    continue
                seen.add(entry.name)

                meta_path = entry / META_FILE
                if meta_path.exists():
                    runs.append(get_run_info(entry.name, entry, "active"))
                else:
                    # Legacy run (no meta.json)
                    runs.append(get_run_info(entry.name, entry, "legacy"))

    return runs


def should_preserve_run(run: RunInfo) -> tuple[bool, str]:
    """Check if a run should be preserved.

    Returns:
        Tuple of (should_preserve, reason)
    """
    # Examples are always preserved
    if run.run_type == "example":
        return True, "example run"

    # Named runs
    preserved_names = get_preserved_named_runs()
    if run.run_id in preserved_names:
        return True, f"named run ({run.run_id})"

    # Prefix patterns
    preserved_prefixes = get_preserved_prefixes()
    for prefix in preserved_prefixes:
        if run.run_id.startswith(prefix):
            return True, f"matches prefix '{prefix}'"

    # Tag-based preservation
    preserved_tags = get_preserved_tags()
    for tag in run.tags:
        if tag in preserved_tags:
            return True, f"has preserved tag '{tag}'"

    return False, ""


def format_size(size_bytes: int) -> str:
    """Format size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def cmd_list(args: argparse.Namespace) -> int:
    """List runs with statistics."""
    runs = discover_all_runs()

    if not runs:
        logger.info("No runs found.")
        return 0

    # Sort by mtime (newest first)
    runs.sort(key=lambda r: r.mtime, reverse=True)

    # Calculate statistics
    total_size = sum(r.size_bytes for r in runs)
    examples = [r for r in runs if r.run_type == "example"]
    active = [r for r in runs if r.run_type == "active"]
    legacy = [r for r in runs if r.run_type == "legacy"]
    corrupt = [r for r in runs if r.is_corrupt]

    logger.info("=" * 60)
    logger.info("RUNS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total runs:     {len(runs)}")
    logger.info(f"  Examples:     {len(examples)}")
    logger.info(f"  Active:       {len(active)}")
    logger.info(f"  Legacy:       {len(legacy)}")
    logger.info(f"  Corrupt:      {len(corrupt)}")
    logger.info(f"Total size:     {format_size(total_size)}")
    logger.info("")

    # Retention policy
    retention_days = get_retention_days()
    max_count = get_max_count()
    logger.info("RETENTION POLICY")
    logger.info(f"  Max age:      {retention_days} days")
    logger.info(f"  Max count:    {max_count}")
    logger.info(f"  Enabled:      {is_retention_enabled()}")
    logger.info("")

    # Show runs if verbose
    if args.verbose:
        logger.info("RUNS (newest first)")
        logger.info("-" * 60)
        for run in runs[:50]:  # Show top 50
            preserve, reason = should_preserve_run(run)
            status = "KEEP" if preserve else "    "
            corrupt_mark = " [CORRUPT]" if run.is_corrupt else ""
            logger.info(
                f"  {status} {run.run_id:<30} "
                f"{run.run_type:<8} "
                f"{run.age_days:>5.1f}d "
                f"{format_size(run.size_bytes):>10}"
                f"{corrupt_mark}"
            )
        if len(runs) > 50:
            logger.info(f"  ... and {len(runs) - 50} more runs")

    # Show what would be deleted
    eligible_for_deletion = []
    for run in runs:
        preserve, _ = should_preserve_run(run)
        if not preserve and run.age_days > retention_days:
            eligible_for_deletion.append(run)

    if eligible_for_deletion:
        logger.info("")
        logger.info(f"CLEANUP CANDIDATES: {len(eligible_for_deletion)} runs")
        logger.info(
            f"  Would free: {format_size(sum(r.size_bytes for r in eligible_for_deletion))}"
        )
        logger.info("  Run 'runs-gc prune' to apply retention policy")

    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    """Apply retention policy to delete old runs."""
    dry_run = args.dry_run or is_dry_run_enabled()
    keep_days = args.days if args.days is not None else get_retention_days()
    keep_count = args.keep if args.keep is not None else get_max_count()

    if not is_retention_enabled() and not args.force:
        logger.info("Retention policy is disabled. Use --force to override.")
        return 0

    runs = discover_all_runs()
    if not runs:
        logger.info("No runs found.")
        return 0

    # Sort by mtime (newest first) for count-based retention
    runs.sort(key=lambda r: r.mtime, reverse=True)

    to_delete: List[RunInfo] = []
    preserved: List[tuple[RunInfo, str]] = []

    for i, run in enumerate(runs):
        # Check preservation rules
        preserve, reason = should_preserve_run(run)
        if preserve:
            preserved.append((run, reason))
            continue

        # Check age
        if run.age_days > keep_days:
            to_delete.append(run)
            continue

        # Check count (after sorting, so we keep newest)
        # Count only non-preserved runs
        non_preserved_index = i - len(preserved)
        if non_preserved_index >= keep_count:
            to_delete.append(run)
            continue

    # Report
    logger.info("=" * 60)
    logger.info("PRUNE OPERATION" + (" (DRY RUN)" if dry_run else ""))
    logger.info("=" * 60)
    logger.info(f"Policy: keep {keep_days} days, max {keep_count} runs")
    logger.info(f"Total runs:      {len(runs)}")
    logger.info(f"To delete:       {len(to_delete)}")
    logger.info(f"Preserved:       {len(preserved)}")
    logger.info(f"Space to free:   {format_size(sum(r.size_bytes for r in to_delete))}")
    logger.info("")

    if not to_delete:
        logger.info("Nothing to delete.")
        return 0

    # Delete
    deleted_count = 0
    for run in to_delete:
        if dry_run:
            logger.info(f"  [DRY-RUN] Would delete: {run.run_id} ({run.age_days:.1f} days old)")
        else:
            try:
                shutil.rmtree(run.path)
                if should_log_deletions():
                    logger.info(f"  Deleted: {run.run_id}")
                deleted_count += 1
            except OSError as e:
                logger.error(f"  Failed to delete {run.run_id}: {e}")

    if not dry_run:
        logger.info("")
        logger.info(f"Deleted {deleted_count} runs.")

    return 0


def cmd_quarantine(args: argparse.Namespace) -> int:
    """Move corrupt runs to quarantine directory."""
    dry_run = args.dry_run or is_dry_run_enabled()

    runs = discover_all_runs()
    corrupt_runs = [r for r in runs if r.is_corrupt]

    if not corrupt_runs:
        logger.info("No corrupt runs found.")
        return 0

    quarantine_dir = RUNS_DIR / "_corrupt"

    logger.info("=" * 60)
    logger.info("QUARANTINE OPERATION" + (" (DRY RUN)" if dry_run else ""))
    logger.info("=" * 60)
    logger.info(f"Corrupt runs found: {len(corrupt_runs)}")
    logger.info(f"Quarantine dir:     {quarantine_dir}")
    logger.info("")

    if not dry_run:
        quarantine_dir.mkdir(parents=True, exist_ok=True)

    quarantined_count = 0
    for run in corrupt_runs:
        dest = quarantine_dir / run.run_id
        if dry_run:
            logger.info(f"  [DRY-RUN] Would quarantine: {run.run_id}")
        else:
            try:
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(run.path), str(dest))
                logger.info(f"  Quarantined: {run.run_id}")
                quarantined_count += 1
            except OSError as e:
                logger.error(f"  Failed to quarantine {run.run_id}: {e}")

    if not dry_run:
        logger.info("")
        logger.info(f"Quarantined {quarantined_count} runs to {quarantine_dir}")

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Runs garbage collection tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    list_parser = subparsers.add_parser("list", help="List runs with statistics")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Show individual runs")

    # prune command
    prune_parser = subparsers.add_parser("prune", help="Apply retention policy")
    prune_parser.add_argument("--keep", type=int, help="Keep at most N runs")
    prune_parser.add_argument("--days", type=int, help="Keep runs younger than N days")
    prune_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    prune_parser.add_argument("--force", action="store_true", help="Run even if retention disabled")

    # quarantine command
    quarantine_parser = subparsers.add_parser("quarantine", help="Move corrupt runs to quarantine")
    quarantine_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be moved"
    )

    args = parser.parse_args()

    if args.command == "list":
        return cmd_list(args)
    elif args.command == "prune":
        return cmd_prune(args)
    elif args.command == "quarantine":
        return cmd_quarantine(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
