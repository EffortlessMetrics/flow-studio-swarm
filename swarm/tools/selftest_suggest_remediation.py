#!/usr/bin/env python3
"""
Selftest Remediation Suggestion Engine

Reads selftest_degradations.log and suggests remediation commands based on
error pattern matching against swarm/config/selftest_remediation_map.yaml.

Design Principle: Read-only suggestions, not auto-execution.
This tool provides actionable guidance for humans to review and run commands.

Usage:
    uv run swarm/tools/selftest_suggest_remediation.py
    uv run swarm/tools/selftest_suggest_remediation.py --degradation-log path/to/log
    uv run swarm/tools/selftest_suggest_remediation.py --severity governance
    uv run swarm/tools/selftest_suggest_remediation.py --json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add repo root to path for library imports. Must run before importing swarm.*,
# since this script is executed by path (e.g. `uv run swarm/tools/selftest_suggest_remediation.py`)
# rather than as a module, so the repo root is not on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from swarm.utils.yaml_utils import load_yaml  # noqa: E402


class RemediationPattern:
    """A single remediation pattern from the map."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.id = data["id"]
        self.error_pattern = data["error_pattern"]
        self.severity = data["severity"]
        self.suggested_commands = data["suggested_commands"]
        self.rationale = data["rationale"]
        self._regex = re.compile(self.error_pattern, re.IGNORECASE)

    def matches(self, error_message: str) -> bool:
        """Check if this pattern matches the given error message."""
        return bool(self._regex.search(error_message))


class DegradationEntry:
    """A single degradation entry from the log."""

    def __init__(
        self,
        timestamp: str,
        step: str,
        status: str,
        error: str,
        severity: Optional[str] = None,
    ) -> None:
        self.timestamp = timestamp
        self.step = step
        self.status = status
        self.error = error
        self.severity = severity or "unknown"


class RemediationSuggestionEngine:
    """Matches degradation logs against remediation patterns."""

    def __init__(self, remediation_map_path: Path) -> None:
        self.remediation_map_path = remediation_map_path
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> List[RemediationPattern]:
        """Load remediation patterns from YAML map."""
        if not self.remediation_map_path.exists():
            raise FileNotFoundError(f"Remediation map not found: {self.remediation_map_path}")

        with open(self.remediation_map_path) as f:
            data = load_yaml(f)

        return [RemediationPattern(p) for p in data["remediation_patterns"]]

    def match_degradation(self, degradation: DegradationEntry) -> Optional[RemediationPattern]:
        """Find the first pattern matching this degradation."""
        for pattern in self.patterns:
            if pattern.matches(degradation.error):
                return pattern
        return None

    def generate_suggestions(
        self, degradations: List[DegradationEntry], severity_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate suggestions for all degradations."""
        suggestions = []
        unmatched_count = 0

        for degradation in degradations:
            # Apply severity filter if specified
            if severity_filter and severity_filter != "all":
                if degradation.severity.lower() != severity_filter.lower():
                    continue

            pattern = self.match_degradation(degradation)

            if pattern:
                suggestions.append(
                    {
                        "degradation": {
                            "timestamp": degradation.timestamp,
                            "step": degradation.step,
                            "status": degradation.status,
                            "error": degradation.error,
                            "severity": degradation.severity,
                        },
                        "remediation": {
                            "id": pattern.id,
                            "suggested_commands": pattern.suggested_commands,
                            "rationale": pattern.rationale,
                        },
                    }
                )
            else:
                unmatched_count += 1

        return {
            "total_degradations": len(degradations),
            "actionable_suggestions": len(suggestions),
            "unmatched": unmatched_count,
            "suggestions": suggestions,
        }


def parse_degradation_log(log_path: Path) -> List[DegradationEntry]:
    """Parse selftest_degradations.log into structured entries."""
    entries = []

    if not log_path.exists():
        return entries

    with open(log_path) as f:
        lines = f.readlines()

    current_entry = None
    timestamp_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    for line in lines:
        line = line.rstrip()

        # Start of a new entry
        if timestamp_pattern.match(line):
            if current_entry:
                entries.append(current_entry)

            parts = line.split(" | ", maxsplit=4)
            if len(parts) >= 5:
                timestamp, step, status, severity, error = parts
                current_entry = DegradationEntry(
                    timestamp=timestamp,
                    step=step,
                    status=status,
                    severity=severity,
                    error=error,
                )
            else:
                current_entry = None
        elif current_entry:
            # Continuation of error message
            current_entry.error += " " + line

    # Don't forget the last entry
    if current_entry:
        entries.append(current_entry)

    return entries


def find_latest_degradation_log(runs_dir: Path) -> Optional[Path]:
    """Find the most recent selftest_degradations.log in runs directory."""
    logs = list(runs_dir.rglob("selftest_degradations.log"))

    if not logs:
        return None

    # Sort by modification time, newest first
    logs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0]


def print_human_readable(result: Dict[str, Any]) -> None:
    """Print suggestions in human-readable format."""
    suggestions = result["suggestions"]
    total = result["total_degradations"]
    actionable = result["actionable_suggestions"]
    unmatched = result["unmatched"]

    print("=== Suggestion Pack ===")
    print(f"Found {total} degradations; {actionable} actionable suggestions\n")

    for i, suggestion in enumerate(suggestions, start=1):
        deg = suggestion["degradation"]
        rem = suggestion["remediation"]

        print(f"--- [{i}/{actionable}] {rem['id']} ---")
        print(f"Step: {deg['step']} (severity: {deg['severity'].upper()})")
        print(f"Error: {deg['error']}\n")
        print("Suggested remediation:")
        for j, cmd in enumerate(rem["suggested_commands"], start=1):
            print(f"  {j}. {cmd}")
        print(f"\nRationale: {rem['rationale']}\n")

    print("=== Summary ===")
    print(f"{actionable} of {total} degradations have actionable suggestions.")
    if unmatched > 0:
        print(f"{unmatched} degradation(s) require human review (not in remediation map).")
    print("\nRun with --dry-run to execute suggested commands (not yet implemented).")


def print_json_output(result: Dict[str, Any]) -> None:
    """Print suggestions in JSON format."""
    print(json.dumps(result, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Suggest remediation commands for selftest degradations (read-only)"
    )
    parser.add_argument(
        "--degradation-log",
        type=Path,
        help="Path to degradation log (default: latest in swarm/runs/)",
    )
    parser.add_argument(
        "--remediation-map",
        type=Path,
        default=Path("swarm/config/selftest_remediation_map.yaml"),
        help="Path to remediation map (default: swarm/config/selftest_remediation_map.yaml)",
    )
    parser.add_argument(
        "--severity",
        choices=["kernel", "governance", "optional", "all"],
        default="all",
        help="Filter suggestions by severity (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    args = parser.parse_args()

    # Find degradation log
    if args.degradation_log:
        log_path = args.degradation_log
    else:
        runs_dir = Path("swarm/runs")
        log_path = find_latest_degradation_log(runs_dir)

        if not log_path:
            print("ERROR: No degradation log found in swarm/runs/", file=sys.stderr)
            print("Run selftest first or specify --degradation-log", file=sys.stderr)
            return 2

    if not log_path.exists():
        print(f"ERROR: Degradation log not found: {log_path}", file=sys.stderr)
        return 2

    # Parse degradation log
    degradations = parse_degradation_log(log_path)

    if not degradations:
        if not args.json:
            print(f"No degradations found in {log_path}")
        else:
            print_json_output(
                {
                    "total_degradations": 0,
                    "actionable_suggestions": 0,
                    "unmatched": 0,
                    "suggestions": [],
                }
            )
        return 0

    # Load remediation engine and generate suggestions
    try:
        engine = RemediationSuggestionEngine(args.remediation_map)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    result = engine.generate_suggestions(degradations, severity_filter=args.severity)

    # Output results
    if args.json:
        print_json_output(result)
    else:
        print_human_readable(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
