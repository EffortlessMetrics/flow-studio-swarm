#!/usr/bin/env python3
"""
List agent model configuration for inspection and oversight.

Shows which agents have inherit vs pinned models, flows they belong to,
and brief description. Primary use: understanding model tier distribution
and quick reference for making model decisions.

CLI usage:
  uv run swarm/tools/list_agent_models.py                 # default table
  uv run swarm/tools/list_agent_models.py --format table  # same
  uv run swarm/tools/list_agent_models.py --format csv    # CSV output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "swarm" / "config" / "agents"


def parse_yaml_simple(content: str) -> Dict[str, Any]:
    """
    Minimal YAML parser for agent config files.
    Extracts: key, flows, model, short_role.
    """
    result: Dict[str, Any] = {}
    current_key = None
    current_list: list[str] = []

    for line in content.splitlines():
        line_stripped = line.strip()

        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith("#"):
            continue

        # Handle list items (flows: - deploy)
        if line_stripped.startswith("- "):
            if current_key == "flows":
                current_list.append(line_stripped[2:].strip())
            continue

        # Handle key: value pairs
        if ":" in line_stripped:
            parts = line_stripped.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""

            # Save previous list if switching keys
            if current_key and current_list:
                result[current_key] = current_list
                current_list = []

            # Remove quotes from string values
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]

            if key in ("key", "model", "short_role", "category", "color"):
                result[key] = value
                current_key = None
            elif key == "flows":
                current_key = "flows"

    # Handle final list if present
    if current_key and current_list:
        result[current_key] = current_list

    return result


def load_agent_configs() -> list[Dict[str, Any]]:
    """Load all agent config files and return structured data."""
    configs: list[Dict[str, Any]] = []

    if not CONFIG_DIR.exists():
        print(f"ERROR: Config directory not found: {CONFIG_DIR}", file=sys.stderr)
        sys.exit(1)

    yaml_files = sorted(CONFIG_DIR.glob("*.yaml"))
    if not yaml_files:
        print(f"WARNING: No config files found in {CONFIG_DIR}", file=sys.stderr)
        return configs

    for yaml_file in yaml_files:
        content = yaml_file.read_text(encoding="utf-8")
        cfg = parse_yaml_simple(content)

        # Normalize flows to comma-separated string
        flows_str = ",".join(cfg.get("flows", [])) if cfg.get("flows") else ""

        configs.append(
            {
                "key": cfg.get("key", yaml_file.stem),
                "model": cfg.get("model", "inherit"),
                "flows": flows_str,
                "short_role": cfg.get("short_role", ""),
                "category": cfg.get("category", ""),
                "color": cfg.get("color", ""),
            }
        )

    return sorted(configs, key=lambda x: x["key"])


def print_table(configs: list[Dict[str, Any]]) -> None:
    """Print agents as human-readable table."""
    if not configs:
        print("No agent configs found.")
        return

    # Compute column widths
    key_width = max(len("key"), max(len(c["key"]) for c in configs))
    flows_width = max(len("flows"), max(len(c["flows"]) for c in configs))
    model_width = max(len("model"), max(len(c["model"]) for c in configs))

    # Header
    print(f"{'key':<{key_width}}  {'flows':<{flows_width}}  {'model':<{model_width}}  category")
    print("-" * (key_width + flows_width + model_width + 30))

    # Rows
    for cfg in configs:
        print(
            f"{cfg['key']:<{key_width}}  {cfg['flows']:<{flows_width}}  {cfg['model']:<{model_width}}  {cfg['category']}"
        )

    # Summary
    print()
    model_counts: Dict[str, int] = {}
    for cfg in configs:
        m = cfg["model"]
        model_counts[m] = model_counts.get(m, 0) + 1

    print("Model Summary:")
    for model in sorted(model_counts.keys()):
        count = model_counts[model]
        print(f"  {model}: {count} agent(s)")


def print_csv(configs: list[Dict[str, Any]]) -> None:
    """Print agents as CSV."""
    if not configs:
        print("No agent configs found.")
        return

    # Header
    print("key,flows,model,category,color")

    # Rows
    for cfg in configs:
        print(f"{cfg['key']},{cfg['flows']},{cfg['model']},{cfg['category']},{cfg['color']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="List agent model configurations for inspection.")
    parser.add_argument(
        "--format",
        choices=["table", "csv"],
        default="table",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    configs = load_agent_configs()

    if args.format == "csv":
        print_csv(configs)
    else:
        print_table(configs)


if __name__ == "__main__":
    main()
