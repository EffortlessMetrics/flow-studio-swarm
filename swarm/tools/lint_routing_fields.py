#!/usr/bin/env python3
"""
Lint script to ensure strict adherence to routing field standards (FR-012).

Checks all python source files for usage of deprecated routing fields.
Enforces the use of `routing_signal` and `handoff_envelope` in V3 architecture.

Exit codes:
  0: Success (clean or warnings only, unless --strict)
  1: Errors found (or warnings in --strict mode)
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Patterns that indicate usage of legacy/deprecated fields
LEGACY_PATTERNS = {
    # These fields are strictly forbidden in V3
    r"route_to_flow": "Deprecated field `route_to_flow`. Use `routing_signal` instead.",
    r"route_to_agent": "Deprecated field `route_to_agent`. Use `handoff_envelope` instead.",
}

# Patterns for transitional/incorrect V3 usage
V3_MALFORMED_PATTERNS = {
    r"routing_signal\s*=\s*['\"][\w_]+['\"]": "Malformed `routing_signal`. Must be a dictionary/object, not a string.",
    r"handoff_envelope\s*=\s*['\"][\w_]+['\"]": "Malformed `handoff_envelope`. Must be a dictionary/object, not a string.",
}

# Files/Directories to skip (legacy, tests, or explicit exceptions)
SKIP_PATTERNS = [
    # System/hidden files
    "__pycache__",
    ".git",
    ".venv",
    ".pytest_cache",
    # Generated/vendor code
    "swarm/tools/flow_studio_ui",
    # Legacy code archives
    "swarm/tools/_archive",
    # Test fixtures that intentionally use legacy formats
    "tests/fixtures",
    # Self-reference (this file checks for patterns it defines)
    "swarm/tools/lint_routing_fields.py",
    # Documentation/Prompts referencing legacy fields for context
    "docs/RELEASE_CHECKLIST.md",
    "swarm/prompts/agentic_steps/self-reviewer.md",
]


def should_skip(path: Path) -> bool:
    """Check if path matches any skip patterns."""
    path_str = str(path)
    return any(p in path_str for p in SKIP_PATTERNS)


def scan_file(path: Path) -> Tuple[List[str], List[str], int]:
    """Scan a single file for violations.

    Returns:
        Tuple of (legacy_errors, v3_errors, v3_usage_count)
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Skip binary files
        return [], [], 0

    legacy_errors = []
    v3_errors = []
    v3_usage_count = 0

    lines = content.splitlines()
    for i, line in enumerate(lines):
        line_num = i + 1

        # Skip comments
        if line.strip().startswith("#"):
            continue

        # Check legacy patterns
        for pattern, msg in LEGACY_PATTERNS.items():
            if re.search(pattern, line):
                legacy_errors.append(f"{path}:{line_num}\n  Pattern: {pattern}\n  Error: {msg}")

        # Check malformed V3 usage
        for pattern, msg in V3_MALFORMED_PATTERNS.items():
            if re.search(pattern, line):
                v3_errors.append(f"{path}:{line_num}\n  Pattern: {pattern}\n  Error: {msg}")

        # Count valid usage for stats
        if "routing_signal" in line or "handoff_envelope" in line:
            v3_usage_count += 1

    return legacy_errors, v3_errors, v3_usage_count


def scan_directory(root: Path) -> Dict[str, Any]:
    """Recursively scan directory for routing field usage."""
    results = {
        "legacy_errors": [],
        "v3_errors": [],
        "v3_usage_count": 0,
        "scanned_files": 0,
    }

    # Files to check - primarily source code
    extensions = {".py", ".ts", ".js", ".md", ".yaml", ".json"}

    for path in root.rglob("*"):
        if path.is_file() and path.suffix in extensions:
            if should_skip(path):
                continue

            results["scanned_files"] += 1
            legacy, v3, count = scan_file(path)

            results["legacy_errors"].extend(legacy)
            results["v3_errors"].extend(v3)
            results["v3_usage_count"] += count

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Lint routing fields for FR-012 compliance"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any legacy usage warnings (transitional patterns)",
    )
    args = parser.parse_args()

    print("Checking for deprecated routing field patterns...")
    if args.strict:
        print("(Strict mode enabled)")

    root_dir = Path(".")
    results = scan_directory(root_dir)

    # Report results
    total_errors = len(results["legacy_errors"]) + len(results["v3_errors"])

    if results["legacy_errors"]:
        print("\n" + "-" * 60)
        print("ERRORS: Legacy/Deprecated fields found")
        print("These must be migrated to V3 routing (routing_signal/handoff_envelope).")
        print("-" * 60)
        for err in results["legacy_errors"]:
            print(f"\n  {err}")

    if results["v3_errors"]:
        print("\n" + "-" * 60)
        print("ERRORS: Malformed V3 fields found")
        print("These usages appear incorrect (e.g. string assignment instead of object).")
        print("-" * 60)
        for err in results["v3_errors"]:
            print(f"\n  {err}")

    # In strict mode, we might want to flag warnings for any mention of legacy fields
    # even if they look like comments or strings, to force cleanup.
    # For now, the regexes catch most usages.

    print("\n" + "-" * 60)
    if total_errors > 0:
        print(f"Summary: {len(results['legacy_errors'])} legacy errors, {len(results['v3_errors'])} malformed V3 errors")
    else:
        print("Summary: No errors found")

    print(f"V3 routing patterns found: {results['v3_usage_count']} valid usages")
    print("-" * 60)

    if total_errors > 0:
        print("\nFAILED: Fix routing field violations")
        sys.exit(1)

    # In strict mode, fail if we found ANY matches for legacy keys
    # (The scan_file logic puts them in legacy_errors, so strict check is implicitly handled above
    # unless we want to separate "warnings" from "errors". Currently treating all as errors.)
    #
    # However, if we wanted to treat some as warnings (e.g. in comments), we'd need smarter regex.
    # For now, assuming code base should be clean.

    print("\nPASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
