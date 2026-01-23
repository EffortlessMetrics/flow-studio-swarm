#!/usr/bin/env python3
"""
Compare profiles or compare a profile to current state.

Usage:
  uv run swarm/tools/profile_diff.py <profile_a> <profile_b>
  uv run swarm/tools/profile_diff.py <profile_a> --current

Examples:
  uv run swarm/tools/profile_diff.py baseline-v1 experimental-v2   # Compare two profiles
  uv run swarm/tools/profile_diff.py baseline-v1 --current         # Compare profile to current state
"""

from __future__ import annotations

import argparse
import difflib
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add swarm package to path for library imports
_SWARM_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from swarm.config.profile_registry import (  # noqa: E402
    PROFILE_DIR,
    ConfigEntry,
    Profile,
    ProfileMeta,
    load_profile,
    profile_exists,
)

__version__ = "1.0.0"

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_added(msg: str) -> None:
    """Print added content in green."""
    print(f"{GREEN}{msg}{RESET}")


def print_removed(msg: str) -> None:
    """Print removed content in red."""
    print(f"{RED}{msg}{RESET}")


def print_changed(msg: str) -> None:
    """Print changed indicator in yellow."""
    print(f"{YELLOW}{msg}{RESET}")


def print_header(msg: str) -> None:
    """Print header in cyan."""
    print(f"{CYAN}{msg}{RESET}")


def print_section(msg: str) -> None:
    """Print section header in magenta."""
    print(f"{MAGENTA}{BOLD}{msg}{RESET}")


def build_profile_from_current() -> Profile:
    """
    Build a Profile object from the current repo configuration.

    Reads:
    - swarm/config/flows.yaml
    - swarm/config/flows/*.yaml
    - swarm/config/agents/*.yaml
    """
    config_dir = _SWARM_ROOT / "swarm" / "config"

    # Read flows.yaml
    flows_yaml_path = config_dir / "flows.yaml"
    flows_yaml = ""
    if flows_yaml_path.exists():
        flows_yaml = flows_yaml_path.read_text(encoding="utf-8")

    # Read per-flow configs
    flow_configs: list[ConfigEntry] = []
    flows_dir = config_dir / "flows"
    if flows_dir.exists():
        for yaml_file in sorted(flows_dir.glob("*.yaml")):
            content = yaml_file.read_text(encoding="utf-8")
            rel_path = str(yaml_file.relative_to(_SWARM_ROOT))
            flow_configs.append(
                ConfigEntry(
                    key=yaml_file.stem,
                    path=rel_path,
                    yaml=content,
                )
            )

    # Read per-agent configs
    agent_configs: list[ConfigEntry] = []
    agents_dir = config_dir / "agents"
    if agents_dir.exists():
        for yaml_file in sorted(agents_dir.glob("*.yaml")):
            content = yaml_file.read_text(encoding="utf-8")
            rel_path = str(yaml_file.relative_to(_SWARM_ROOT))
            agent_configs.append(
                ConfigEntry(
                    key=yaml_file.stem,
                    path=rel_path,
                    yaml=content,
                )
            )

    # Create profile metadata
    meta = ProfileMeta(
        id="<current>",
        label="Current Configuration",
        description="Current state of the repository",
        created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        created_by=None,
    )

    return Profile(
        meta=meta,
        flows_yaml=flows_yaml,
        flow_configs=flow_configs,
        agent_configs=agent_configs,
    )


def format_unified_diff(
    content_a: str,
    content_b: str,
    filename_a: str,
    filename_b: str,
    use_color: bool = True,
) -> list[str]:
    """Generate unified diff between two strings."""
    lines_a = content_a.splitlines(keepends=True)
    lines_b = content_b.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=filename_a,
            tofile=filename_b,
        )
    )

    if not use_color:
        return diff_lines

    # Colorize the output
    colored_lines = []
    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---"):
            colored_lines.append(f"{BOLD}{line}{RESET}")
        elif line.startswith("@@"):
            colored_lines.append(f"{CYAN}{line}{RESET}")
        elif line.startswith("+"):
            colored_lines.append(f"{GREEN}{line}{RESET}")
        elif line.startswith("-"):
            colored_lines.append(f"{RED}{line}{RESET}")
        else:
            colored_lines.append(line)

    return colored_lines


def compare_flows_yaml(
    profile_a: Profile,
    profile_b: Profile,
    name_a: str,
    name_b: str,
) -> bool:
    """Compare flows.yaml between two profiles. Returns True if different."""
    if profile_a.flows_yaml == profile_b.flows_yaml:
        return False

    print_section("\n=== flows.yaml ===")
    diff_lines = format_unified_diff(
        profile_a.flows_yaml,
        profile_b.flows_yaml,
        f"{name_a}/flows.yaml",
        f"{name_b}/flows.yaml",
    )
    for line in diff_lines:
        print(line, end="")
    print()
    return True


def compare_config_entries(
    entries_a: list[ConfigEntry],
    entries_b: list[ConfigEntry],
    name_a: str,
    name_b: str,
    category: str,
) -> tuple[int, int, int]:
    """
    Compare config entries between two profiles.

    Returns: (added_count, removed_count, changed_count)
    """
    # Build lookup dictionaries
    dict_a = {e.key: e for e in entries_a}
    dict_b = {e.key: e for e in entries_b}

    keys_a = set(dict_a.keys())
    keys_b = set(dict_b.keys())

    added = keys_b - keys_a
    removed = keys_a - keys_b
    common = keys_a & keys_b

    added_count = len(added)
    removed_count = len(removed)
    changed_count = 0

    # Show added entries
    if added:
        print_section(f"\n=== {category}: Added ===")
        for key in sorted(added):
            print_added(f"+ {key}")
        print()

    # Show removed entries
    if removed:
        print_section(f"\n=== {category}: Removed ===")
        for key in sorted(removed):
            print_removed(f"- {key}")
        print()

    # Show changed entries
    for key in sorted(common):
        entry_a = dict_a[key]
        entry_b = dict_b[key]

        if entry_a.yaml != entry_b.yaml:
            changed_count += 1
            print_section(f"\n=== {category}: {key} ===")
            diff_lines = format_unified_diff(
                entry_a.yaml,
                entry_b.yaml,
                f"{name_a}/{entry_a.path}",
                f"{name_b}/{entry_b.path}",
            )
            for line in diff_lines:
                print(line, end="")
            print()

    return added_count, removed_count, changed_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare profiles or compare a profile to current state.",
        epilog="Profiles are loaded from swarm/profiles/<profile_id>.swarm_profile.yaml",
    )
    parser.add_argument(
        "profile_a",
        help="First profile ID to compare",
    )
    parser.add_argument(
        "profile_b",
        nargs="?",
        default=None,
        help="Second profile ID to compare (optional if --current is used)",
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Compare profile_a to the current repo state",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"profile_diff {__version__}",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.current and not args.profile_b:
        parser.error("Either provide profile_b or use --current")

    if args.current and args.profile_b:
        parser.error("Cannot use both profile_b and --current")

    # Check if profile_a exists
    if not profile_exists(args.profile_a):
        print(f"{RED}Error: Profile '{args.profile_a}' not found.{RESET}", file=sys.stderr)
        print(f"Looking in: {PROFILE_DIR}", file=sys.stderr)
        sys.exit(1)

    # Load or build profiles
    try:
        profile_a = load_profile(args.profile_a)
        name_a = args.profile_a

        if args.current:
            profile_b = build_profile_from_current()
            name_b = "<current>"
        else:
            if not profile_exists(args.profile_b):
                print(f"{RED}Error: Profile '{args.profile_b}' not found.{RESET}", file=sys.stderr)
                sys.exit(1)
            profile_b = load_profile(args.profile_b)
            name_b = args.profile_b

    except Exception as e:
        print(f"{RED}Error: Failed to load profile: {e}{RESET}", file=sys.stderr)
        sys.exit(1)

    # Print comparison header
    print(f"\n{BOLD}Comparing profiles:{RESET}")
    print(f"  A: {name_a} ({profile_a.meta.label})")
    print(f"  B: {name_b} ({profile_b.meta.label})")
    print()

    # Track differences
    has_differences = False

    # Compare flows.yaml
    if compare_flows_yaml(profile_a, profile_b, name_a, name_b):
        has_differences = True

    # Compare flow configs
    flow_added, flow_removed, flow_changed = compare_config_entries(
        profile_a.flow_configs,
        profile_b.flow_configs,
        name_a,
        name_b,
        "Flow Configs",
    )
    if flow_added or flow_removed or flow_changed:
        has_differences = True

    # Compare agent configs
    agent_added, agent_removed, agent_changed = compare_config_entries(
        profile_a.agent_configs,
        profile_b.agent_configs,
        name_a,
        name_b,
        "Agent Configs",
    )
    if agent_added or agent_removed or agent_changed:
        has_differences = True

    # Print summary
    print_section("\n=== Summary ===")
    print()

    if not has_differences:
        print(f"{GREEN}No differences found between profiles.{RESET}")
    else:
        if profile_a.flows_yaml != profile_b.flows_yaml:
            print_changed("  flows.yaml: changed")

        print()
        print(f"  {BOLD}Flow Configs:{RESET}")
        print(f"    Added: {flow_added}")
        print(f"    Removed: {flow_removed}")
        print(f"    Changed: {flow_changed}")

        print()
        print(f"  {BOLD}Agent Configs:{RESET}")
        print(f"    Added: {agent_added}")
        print(f"    Removed: {agent_removed}")
        print(f"    Changed: {agent_changed}")

    print()

    # Exit with code indicating if differences were found
    sys.exit(1 if has_differences else 0)


if __name__ == "__main__":
    main()
