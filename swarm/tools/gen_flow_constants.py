#!/usr/bin/env python3
"""
gen_flow_constants.py - Generate TypeScript constants from flows.yaml

Reads flow ordering from swarm/config/flows.yaml and generates TypeScript
constants for Flow Studio at swarm/tools/flow_studio_ui/src/flow_constants.ts.

Usage:
    uv run swarm/tools/gen_flow_constants.py           # Generate
    uv run swarm/tools/gen_flow_constants.py --check   # Check if up-to-date

Exit codes:
    0 - Success (generated or check passed)
    1 - Failure (check failed, file out of date)
    2 - Error (missing source file)
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add swarm package to path for library imports
_SWARM_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from swarm.utils.yaml_utils import load_yaml  # noqa: E402

# Project root (two levels up from this script)
PROJECT_ROOT = Path(__file__).parent.parent.parent
FLOWS_YAML = PROJECT_ROOT / "swarm" / "config" / "flows.yaml"
OUTPUT_TS = PROJECT_ROOT / "swarm" / "tools" / "flow_studio_ui" / "src" / "flow_constants.ts"

TEMPLATE = """// AUTO-GENERATED from swarm/config/flows.yaml
// Do not edit manually. Run: make gen-flow-constants

/** Canonical flow ordering in SDLC sequence */
export const FLOW_KEYS = {keys} as const;

/** Valid flow keys derived from FLOW_KEYS constant */
export type FlowKey = typeof FLOW_KEYS[number];

/** Flow key to numeric index (1-9) */
export const FLOW_INDEX: Record<FlowKey, number> = {{
{index_entries}
}};

/** Flow key to display title */
export const FLOW_TITLES: Record<FlowKey, string> = {{
{title_entries}
}};

/** Flow key to description */
export const FLOW_DESCRIPTIONS: Record<FlowKey, string> = {{
{description_entries}
}};
"""


def load_flows() -> List[Dict[str, Any]]:
    """Load flows from the consolidated flows.yaml file."""
    if not FLOWS_YAML.exists():
        print(f"Error: {FLOWS_YAML} not found")
        sys.exit(2)

    with open(FLOWS_YAML, "r") as f:
        data = load_yaml(f)

    if not data or "flows" not in data:
        print(f"Error: {FLOWS_YAML} is missing 'flows' key")
        sys.exit(2)

    return data["flows"]


def generate_typescript(flows: List[Dict[str, Any]]) -> str:
    """Generate TypeScript constants from flow data."""
    # Build FLOW_KEYS array
    keys = [f["key"] for f in flows]
    keys_str = "[" + ", ".join(f'"{k}"' for k in keys) + "]"

    # Helper to quote keys that need it (contain hyphens, etc.)
    def quote_key(key: str) -> str:
        if "-" in key or not key.isidentifier():
            return f'"{key}"'
        return key

    # Build FLOW_INDEX entries
    index_entries = []
    for f in flows:
        k = quote_key(f["key"])
        index_entries.append(f"  {k}: {f['index']},")

    # Build FLOW_TITLES entries
    title_entries = []
    for f in flows:
        k = quote_key(f["key"])
        title_entries.append(f'  {k}: "{f["short_title"]}",')

    # Build FLOW_DESCRIPTIONS entries
    description_entries = []
    for f in flows:
        k = quote_key(f["key"])
        # Escape any double quotes in the description
        desc = f["description"].replace('"', '\\"')
        description_entries.append(f'  {k}: "{desc}",')

    return TEMPLATE.format(
        keys=keys_str,
        index_entries="\n".join(index_entries),
        title_entries="\n".join(title_entries),
        description_entries="\n".join(description_entries),
    )


def write_output(content: str) -> bool:
    """Write the generated TypeScript to the output file."""
    # Ensure parent directory exists
    OUTPUT_TS.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_TS, "w") as f:
        f.write(content)

    return True


def check_output(content: str) -> bool:
    """Check if generated content matches existing file."""
    if not OUTPUT_TS.exists():
        print(f"ERROR: {OUTPUT_TS} does not exist")
        return False

    with open(OUTPUT_TS, "r") as f:
        existing = f.read()

    if content == existing:
        print(f"OK: {OUTPUT_TS} is up to date")
        return True
    else:
        print(f"ERROR: {OUTPUT_TS} is out of date. Run: make gen-flow-constants")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate TypeScript flow constants from flows.yaml"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if generated file is up-to-date (don't regenerate)",
    )
    args = parser.parse_args()

    # Load flow data
    flows = load_flows()

    if not flows:
        print(f"Warning: No flows found in {FLOWS_YAML}")
        sys.exit(2)

    # Generate TypeScript content
    generated = generate_typescript(flows)

    if args.check:
        # Check mode
        success = check_output(generated)
        sys.exit(0 if success else 1)
    else:
        # Generate mode
        write_output(generated)
        print(f"Generated {OUTPUT_TS}")
        sys.exit(0)


if __name__ == "__main__":
    main()
