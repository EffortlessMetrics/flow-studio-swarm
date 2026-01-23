#!/usr/bin/env python3
"""
Apply a profile to the repo.

Usage:
  uv run swarm/tools/profile_load.py <profile_id>                    # Dry-run (default)
  uv run swarm/tools/profile_load.py <profile_id> --apply            # Apply with backup required
  uv run swarm/tools/profile_load.py <profile_id> --apply --backup   # Apply with backup (safest)
  uv run swarm/tools/profile_load.py <profile_id> --apply --force    # Apply without backup (dangerous)

Examples:
  uv run swarm/tools/profile_load.py baseline-v1                     # Preview changes (safe)
  uv run swarm/tools/profile_load.py baseline-v1 --apply --backup    # Apply with backups
  uv run swarm/tools/profile_load.py baseline-v1 --apply --force     # Apply without backup
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add swarm package to path for library imports
_SWARM_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from swarm.config.profile_registry import (  # noqa: E402
    PROFILE_DIR,
    load_profile,
    profile_exists,
    set_current_profile,
)

__version__ = "1.0.0"

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_success(msg: str) -> None:
    """Print success message in green."""
    print(f"{GREEN}{msg}{RESET}")


def print_warning(msg: str) -> None:
    """Print warning message in yellow."""
    print(f"{YELLOW}{msg}{RESET}")


def print_error(msg: str) -> None:
    """Print error message in red."""
    print(f"{RED}{msg}{RESET}", file=sys.stderr)


def print_info(msg: str) -> None:
    """Print info message in cyan."""
    print(f"{CYAN}{msg}{RESET}")


def print_banner(msg: str, style: str = "info") -> None:
    """Print a prominent banner."""
    if style == "dry_run":
        print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
        print(f"{BOLD}{CYAN}  {msg}{RESET}")
        print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n")
    elif style == "apply":
        print(f"\n{BOLD}{YELLOW}{'=' * 60}{RESET}")
        print(f"{BOLD}{YELLOW}  {msg}{RESET}")
        print(f"{BOLD}{YELLOW}{'=' * 60}{RESET}\n")
    else:
        print(f"\n{msg}\n")


def is_git_tree_dirty() -> bool:
    """Check if the git tree has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=_SWARM_ROOT,
            check=True,
        )
        return bool(result.stdout.strip())
    except subprocess.SubprocessError:
        # If git command fails, assume clean to not block
        return False


def get_current_git_branch() -> str | None:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=_SWARM_ROOT,
            check=True,
        )
        return result.stdout.strip() or None
    except subprocess.SubprocessError:
        return None


def create_backup(file_path: Path, backup_dir: Path) -> Path | None:
    """Create a backup of a file if it exists."""
    if not file_path.exists():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / file_path.name
    shutil.copy2(file_path, backup_path)
    return backup_path


def write_file(
    file_path: Path,
    content: str,
    dry_run: bool,
    backup_dir: Path | None = None,
) -> tuple[bool, str]:
    """
    Write content to file.

    Returns:
        (created_new, status_message)
    """
    is_new = not file_path.exists()

    if dry_run:
        if is_new:
            return True, f"[dry-run] Would create: {file_path}"
        else:
            return False, f"[dry-run] Would update: {file_path}"

    # Create backup if requested
    if backup_dir and file_path.exists():
        backup_path = create_backup(file_path, backup_dir)
        if backup_path:
            print(f"  Backed up: {file_path.name} -> {backup_path}")

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    file_path.write_text(content, encoding="utf-8")

    if is_new:
        return True, f"Created: {file_path}"
    else:
        return False, f"Updated: {file_path}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply a profile to the repo.",
        epilog="Loads from swarm/profiles/<profile_id>.swarm_profile.yaml",
    )
    parser.add_argument(
        "profile_id",
        help="Profile ID to load",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes (without this flag, runs in dry-run mode)",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backups of existing files before overwriting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip safety checks (backup requirement, git tree check)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"profile_load {__version__}",
    )

    args = parser.parse_args()

    # Determine if this is a dry run (default: yes)
    dry_run = not args.apply

    # Check if profile exists
    if not profile_exists(args.profile_id):
        print_error(f"Error: Profile '{args.profile_id}' not found.")
        print_error(f"Looking in: {PROFILE_DIR}")
        sys.exit(1)

    # Print mode banner
    if dry_run:
        print_banner(
            "DRY RUN -- showing what would change; no files written.",
            style="dry_run",
        )
    else:
        # Safety check: require --backup or --force for live apply
        if not args.backup and not args.force:
            print_error("Error: --apply requires either --backup or --force")
            print_error("")
            print_error("  Safe usage:    --apply --backup   (recommended)")
            print_error("  Dangerous:     --apply --force    (no backup)")
            print_error("")
            print_error("Aborting to protect existing files.")
            sys.exit(1)

        # Safety check: git tree must be clean (unless --force)
        if not args.force and is_git_tree_dirty():
            print_error("Error: Git tree has uncommitted changes.")
            print_error("")
            print_error("  Commit or stash your changes first, or use --force to override.")
            print_error("")
            print_error("Aborting to protect uncommitted work.")
            sys.exit(1)

        print_banner(
            f'Applying profile "{args.profile_id}" -- backing up and writing files.',
            style="apply",
        )

    # Load the profile
    print(f"{BOLD}Loading profile '{args.profile_id}'...{RESET}")

    try:
        profile = load_profile(args.profile_id)
    except Exception as e:
        print_error(f"Error: Failed to load profile: {e}")
        sys.exit(1)

    print(f"  Label: {profile.meta.label}")
    print(f"  Created: {profile.meta.created_at}")
    if profile.meta.description:
        print(f"  Description: {profile.meta.description}")
    print()

    # Setup backup directory if requested
    backup_dir: Path | None = None
    if args.backup and not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = _SWARM_ROOT / "swarm" / "backups" / f"profile_backup_{timestamp}"
        print(f"Backups will be saved to: {backup_dir}")
        print()

    # Track statistics
    stats = {
        "created": 0,
        "updated": 0,
        "errors": 0,
    }

    # Write flows.yaml
    print(f"{BOLD}Writing flows.yaml...{RESET}")
    flows_yaml_path = _SWARM_ROOT / "swarm" / "config" / "flows.yaml"
    if profile.flows_yaml:
        try:
            is_new, msg = write_file(flows_yaml_path, profile.flows_yaml, dry_run, backup_dir)
            print(f"  {msg}")
            if is_new:
                stats["created"] += 1
            else:
                stats["updated"] += 1
        except Exception as e:
            print_error(f"  Error: {e}")
            stats["errors"] += 1
    else:
        print_warning("  Skipped: No flows_yaml content in profile")
    print()

    # Write flow configs
    print(f"{BOLD}Writing flow configs ({len(profile.flow_configs)})...{RESET}")
    for config in profile.flow_configs:
        file_path = _SWARM_ROOT / config.path
        try:
            is_new, msg = write_file(file_path, config.yaml, dry_run, backup_dir)
            print(f"  {msg}")
            if is_new:
                stats["created"] += 1
            else:
                stats["updated"] += 1
        except Exception as e:
            print_error(f"  Error writing {config.path}: {e}")
            stats["errors"] += 1
    print()

    # Write agent configs
    print(f"{BOLD}Writing agent configs ({len(profile.agent_configs)})...{RESET}")
    for config in profile.agent_configs:
        file_path = _SWARM_ROOT / config.path
        try:
            is_new, msg = write_file(file_path, config.yaml, dry_run, backup_dir)
            print(f"  {msg}")
            if is_new:
                stats["created"] += 1
            else:
                stats["updated"] += 1
        except Exception as e:
            print_error(f"  Error writing {config.path}: {e}")
            stats["errors"] += 1
    print()

    # Print summary
    print(f"{BOLD}Summary:{RESET}")
    print(f"  Files created: {stats['created']}")
    print(f"  Files updated: {stats['updated']}")
    if stats["errors"] > 0:
        print_error(f"  Errors: {stats['errors']}")
    print()

    if dry_run:
        print_info("DRY RUN complete - no files were modified")
        print_info("To apply changes, run with: --apply --backup")
    elif stats["errors"] == 0:
        # Track the current profile
        source_branch = get_current_git_branch()
        set_current_profile(args.profile_id, profile.meta.label, source_branch)
        print_success("Profile applied successfully!")
        print_info("Next: make gen-flow-constants && make gen-adapters && make ts-build")
    else:
        print_warning("Profile applied with some errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
