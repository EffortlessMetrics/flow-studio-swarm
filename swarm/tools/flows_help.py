#!/usr/bin/env python3
"""
flows_help.py - Quick reference for swarm flows.

Lists all available flows, their configs, and common tasks.

Usage (from repo root):

    uv run swarm/tools/flows_help.py

Dependencies:
  - PyYAML (included in project)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Add repo root to path for imports
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from swarm.config.flow_registry import get_flow_index, get_flow_keys  # noqa: E402
from swarm.utils.yaml_utils import load_yaml  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
FLOW_CONFIG_DIR = REPO_ROOT / "swarm" / "config" / "flows"


# ---------------------------------------------------------------------------
# Flow loader
# ---------------------------------------------------------------------------


def load_flows() -> Dict[str, Any]:
    """Load all flow configs from swarm/config/flows/*.yaml"""
    flows = {}
    if not FLOW_CONFIG_DIR.exists():
        return flows

    for flow_file in sorted(FLOW_CONFIG_DIR.glob("*.yaml")):
        try:
            with open(flow_file) as f:
                config = load_yaml(f)
                if config and "key" in config:
                    flows[config["key"]] = config
        except Exception as e:
            print(f"Warning: Failed to load {flow_file}: {e}", flush=True)

    return flows


def format_flow_title(flow: Dict[str, Any]) -> str:
    """Extract flow number and title."""
    title = flow.get("title", "")
    # Extract "Flow N" from title like "Flow 1 - Signal → Spec (Shaping)"
    if " - " in title:
        return title.split(" - ", 1)[1].strip()
    return title


def format_steps_count(flow: Dict[str, Any]) -> int:
    """Count steps in a flow."""
    return len(flow.get("steps", []))


def print_header():
    """Print the main help header."""
    print()
    print("Swarm Flows — Quick Reference")
    print("=" * 70)
    print()


def print_flows_list(flows: Dict[str, Any]):
    """Print concise list of all flows."""
    print("Available Flows:")
    print("-" * 70)
    print()

    # Order flows by their natural sequence
    for key in get_flow_keys():
        if key not in flows:
            continue

        flow = flows[key]
        # Get flow number from registry
        flow_num = get_flow_index(key)

        title = format_flow_title(flow)
        steps = format_steps_count(flow)
        config_path = f"swarm/config/flows/{key}.yaml"

        print(f"  Flow {flow_num}: {key:8s} → {title:50s}")
        print(f"             Config:  {config_path}")
        print(f"             Steps:   {steps}")
        print()


def print_common_tasks():
    """Print common workflow commands."""
    print("Common Tasks:")
    print("-" * 70)
    print()
    print("  make flow-studio              # Visualize flows at http://localhost:5000")
    print("  make gen-flows                # Regenerate flow docs from YAML configs")
    print("  make check-flows              # Validate that docs are in sync with YAML")
    print("  make validate-swarm           # Full swarm validation (agents + flows)")
    print()


def print_editing_workflow():
    """Print workflow for editing flows."""
    print("Editing Workflow:")
    print("-" * 70)
    print()
    print("  1. Edit flow config:")
    print("     $EDITOR swarm/config/flows/<key>.yaml")
    print()
    print("  2. Regenerate documentation:")
    print("     make gen-flows")
    print()
    print("  3. Verify alignment:")
    print("     make check-flows")
    print()
    print("  4. Run full validation:")
    print("     make validate-swarm")
    print()


def print_footer():
    """Print closing note."""
    print("For detailed flow information, see:")
    print("  - CLAUDE.md § Development Workflow")
    print("  - swarm/flows/flow-*.md (detailed specs)")
    print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="flows_help",
        description=(
            "Swarm Flows Quick Reference\n\n"
            "Lists all available flows, their configs, and common tasks.\n"
            "Reads from swarm/config/flows/*.yaml."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Parse args (just to enable --help)
    parser.parse_args()

    flows = load_flows()

    print_header()
    print_flows_list(flows)
    print_common_tasks()
    print_editing_workflow()
    print_footer()


if __name__ == "__main__":
    main()
