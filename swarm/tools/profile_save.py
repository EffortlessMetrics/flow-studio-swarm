#!/usr/bin/env python3
"""
Export current swarm config as a profile.

Usage:
  uv run swarm/tools/profile_save.py <profile_id> [--label "Human Label"] [--description "Description"]

Example:
  uv run swarm/tools/profile_save.py baseline-v1 --label "Baseline Configuration" --description "Initial config snapshot"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add swarm package to path for library imports
_SWARM_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from datetime import datetime, timezone  # noqa: E402

from swarm.config.profile_registry import (  # noqa: E402
    ConfigEntry,
    Profile,
    ProfileMeta,
    profile_exists,
    save_profile,
)

__version__ = "1.0.0"

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
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


def build_profile_from_current(
    profile_id: str,
    label: str,
    description: str,
) -> Profile:
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
    else:
        print_warning(f"Warning: {flows_yaml_path} not found")

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
        print(f"  Found {len(flow_configs)} flow configs")
    else:
        print_warning(f"Warning: {flows_dir} not found")

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
        print(f"  Found {len(agent_configs)} agent configs")
    else:
        print_warning(f"Warning: {agents_dir} not found")

    # Create profile metadata
    meta = ProfileMeta(
        id=profile_id,
        label=label,
        description=description,
        created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        created_by=None,
    )

    return Profile(
        meta=meta,
        flows_yaml=flows_yaml,
        flow_configs=flow_configs,
        agent_configs=agent_configs,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export current swarm config as a profile.",
        epilog="Profile will be saved to swarm/profiles/<profile_id>.swarm_profile.yaml",
    )
    parser.add_argument(
        "profile_id",
        help="Unique identifier for the profile (e.g., baseline-v1)",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Human-readable label for the profile",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Description of the profile",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing profile if it exists",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"profile_save {__version__}",
    )

    args = parser.parse_args()

    # Check if profile already exists
    if profile_exists(args.profile_id) and not args.force:
        print_error(f"Error: Profile '{args.profile_id}' already exists.")
        print_error("Use --force to overwrite.")
        sys.exit(1)

    # Use profile_id as label if not specified
    label = args.label or args.profile_id

    print(f"\n{BOLD}Building profile '{args.profile_id}'...{RESET}")

    try:
        # Build profile from current state
        profile = build_profile_from_current(
            profile_id=args.profile_id,
            label=label,
            description=args.description,
        )

        # Save the profile
        saved_path = save_profile(profile)

        print()
        print_success("Profile saved successfully!")
        print(f"  {BOLD}Path:{RESET} {saved_path}")
        print(f"  {BOLD}ID:{RESET} {profile.meta.id}")
        print(f"  {BOLD}Label:{RESET} {profile.meta.label}")
        print(f"  {BOLD}Flows:{RESET} {len(profile.flow_configs)} configs")
        print(f"  {BOLD}Agents:{RESET} {len(profile.agent_configs)} configs")
        print(f"  {BOLD}Created:{RESET} {profile.meta.created_at}")
        print()

    except Exception as e:
        print_error(f"Error: Failed to save profile: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
