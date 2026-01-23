#!/usr/bin/env python3
"""
show_selftest_degradations.py - Display selftest degradation log in human-readable or JSON format.

Usage:
    uv run swarm/tools/show_selftest_degradations.py              # Human-readable output
    uv run swarm/tools/show_selftest_degradations.py --json       # JSON output
    uv run swarm/tools/show_selftest_degradations.py --json-v2    # JSON with metadata

This script reads selftest_degradations.log (JSONL format) and formats it for consumption.
The log is created by the selftest system when running in degraded mode and non-blocking
(GOVERNANCE/OPTIONAL) steps fail.

## Degradation Log Schema (AC-6)

Each line in selftest_degradations.log is a JSON object with these required fields:

  timestamp:  ISO 8601 timestamp (e.g., "2025-12-01T10:15:22+00:00")
  step_id:    Unique step identifier (e.g., "agents-governance")
  step_name:  Human-readable step description
  tier:       Selftest tier ("kernel", "governance", "optional")
  message:    Failure message (stderr or stdout from failed step)
  severity:   Severity level ("critical", "warning", "info")
  remediation: Suggested fix command

Example entry:
  {
    "timestamp": "2025-12-01T10:15:22+00:00",
    "step_id": "agents-governance",
    "step_name": "Agent definitions linting and formatting",
    "tier": "governance",
    "message": "Agent 'foo-bar' not found in registry",
    "severity": "warning",
    "remediation": "Run: make selftest --step agents-governance for details"
  }
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def load_degradations() -> List[Dict[str, Any]]:
    """Load and parse JSONL degradation log."""
    log_path = Path("selftest_degradations.log")

    if not log_path.exists():
        return []

    entries: List[Dict[str, Any]] = []
    try:
        with log_path.open(encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Validate required fields
                    required = {
                        "timestamp",
                        "step_id",
                        "step_name",
                        "tier",
                        "message",
                        "severity",
                        "remediation",
                    }
                    missing = required - set(entry.keys())
                    if missing:
                        print(
                            f"Warning: Line {line_num} missing fields: {missing}", file=sys.stderr
                        )
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    print(f"Warning: Line {line_num} is not valid JSON: {e}", file=sys.stderr)
                    continue
    except IOError as e:
        print(f"Error reading degradation log: {e}", file=sys.stderr)
        return []

    return entries


def format_timestamp(ts_str: str) -> str:
    """Format ISO 8601 timestamp to readable string."""
    try:
        ts_obj = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return ts_obj.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, AttributeError):
        return ts_str


def print_human_readable(entries: List[Dict[str, Any]]) -> None:
    """Print degradations in human-readable format."""
    if not entries:
        print("No selftest_degradations.log found or log is empty.")
        print()
        print("This file is created when running selftest in degraded mode.")
        print("  Run: uv run swarm/tools/selftest.py --degraded")
        return

    print("=" * 70)
    print("SELFTEST DEGRADATIONS")
    print("=" * 70)
    print()

    for entry in entries:
        ts_str = entry.get("timestamp", "?")
        tier = entry.get("tier", "?")
        step_id = entry.get("step_id", "?")
        step_name = entry.get("step_name", "?")
        severity = entry.get("severity", "?").upper()
        message = entry.get("message", "").strip()
        remediation = entry.get("remediation", "")

        ts_pretty = format_timestamp(ts_str)

        print(f"[{ts_pretty}] {tier.upper()}/{step_id}")
        print(f"  Severity: {severity}")
        print(f"  Step:     {step_name}")
        if message:
            # Truncate long messages for readability
            if len(message) > 100:
                message = message[:97] + "..."
            print(f"  Message:  {message}")
        if remediation:
            print(f"  Fix:      {remediation}")
        print()

    print("=" * 70)
    print(f"Total degradations: {len(entries)}")
    print()
    print("To see all steps and tiers, run:")
    print("  uv run swarm/tools/selftest.py --plan")
    print()
    print("To run a specific step and investigate, run:")
    print("  uv run swarm/tools/selftest.py --step <step-id>")
    print()


def print_json(entries: List[Dict[str, Any]], pretty: bool = True) -> None:
    """Print degradations as JSON."""
    if pretty:
        print(json.dumps(entries, indent=2))
    else:
        print(json.dumps(entries))


def print_json_v2(entries: List[Dict[str, Any]]) -> None:
    """Print degradations in v2 format with metadata."""
    output = {
        "version": "2.0",
        "metadata": {
            "timestamp": datetime.now(datetime.now().astimezone().tzinfo).isoformat(),
            "log_file": "selftest_degradations.log",
            "total_entries": len(entries),
        },
        "entries": entries,
    }
    print(json.dumps(output, indent=2))


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Display selftest degradation log (AC-6 schema)",
        epilog="See docs/SELFTEST_SYSTEM.md for schema details.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (JSONL parsed into array)",
    )
    parser.add_argument(
        "--json-v2",
        action="store_true",
        help="Output as JSON v2 with metadata",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="show_selftest_degradations.py 1.0",
    )

    args = parser.parse_args()

    entries = load_degradations()

    if args.json_v2:
        print_json_v2(entries)
    elif args.json:
        print_json(entries, pretty=True)
    else:
        print_human_readable(entries)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
