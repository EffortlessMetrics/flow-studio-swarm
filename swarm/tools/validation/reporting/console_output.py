# swarm/tools/validation/reporting/console_output.py
"""Console output formatters for validation results."""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List

from swarm.validator import ValidationError, ValidationResult

from .json_output import build_detailed_json_output


def print_json_output(
    result: ValidationResult,
    registry: Dict[str, Dict[str, Any]],
    parse_flow_config: Callable[[Path], Dict[str, Any]],
) -> None:
    """Print JSON output to stdout.

    Args:
        result: The validation result containing errors and warnings
        registry: The agent registry dictionary
        parse_flow_config: Function to parse flow config files
    """
    output = build_detailed_json_output(result, registry, parse_flow_config)
    print(json.dumps(output, indent=2))


def print_success(result: ValidationResult) -> None:
    """Print success message to stdout, including warnings if any.

    Args:
        result: The validation result (may contain warnings)
    """
    print("Swarm validation PASSED.")
    print("  [PASS] All agents conform to Claude Code platform spec")
    print("  [PASS] All agents follow swarm design constraints")
    print("  [PASS] Flow specs reference valid agents")

    # Print warnings if any (they don't fail validation)
    if result.has_warnings():
        warnings_by_type: Dict[str, List[ValidationError]] = defaultdict(list)
        for warning in result.sorted_warnings():
            warnings_by_type[warning.error_type].append(warning)

        print("\n", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print("WARNINGS (design guidelines, not errors):", file=sys.stderr)
        print("=" * 70, file=sys.stderr)

        for warn_type in sorted(warnings_by_type.keys()):
            warnings = warnings_by_type[warn_type]
            print(f"\n{warn_type} Warnings ({len(warnings)}):", file=sys.stderr)
            for warning in warnings:
                print(warning.format().replace("[FAIL]", "[WARN]"), file=sys.stderr)

        print("\nNote: Warnings indicate swarm design guideline violations.", file=sys.stderr)
        print("      Use --strict flag to treat warnings as errors.", file=sys.stderr)


def print_errors(result: ValidationResult) -> None:
    """Print errors and warnings to stderr in deterministic order.

    Args:
        result: The validation result containing errors and warnings
    """
    # Group errors by type
    by_type: Dict[str, List[ValidationError]] = defaultdict(list)
    for error in result.sorted_errors():
        by_type[error.error_type].append(error)

    # Print errors grouped by type
    for error_type in sorted(by_type.keys()):
        errors = by_type[error_type]
        print(f"\n{error_type} Errors ({len(errors)}):", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        for error in errors:
            print(error.format(), file=sys.stderr)

    # Print warnings if any
    if result.has_warnings():
        warnings_by_type: Dict[str, List[ValidationError]] = defaultdict(list)
        for warning in result.sorted_warnings():
            warnings_by_type[warning.error_type].append(warning)

        print("\n", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print("WARNINGS (design guidelines, not errors):", file=sys.stderr)
        print("=" * 70, file=sys.stderr)

        for warn_type in sorted(warnings_by_type.keys()):
            warnings = warnings_by_type[warn_type]
            print(f"\n{warn_type} Warnings ({len(warnings)}):", file=sys.stderr)
            for warning in warnings:
                print(warning.format().replace("[FAIL]", "[WARN]"), file=sys.stderr)

        print("\nNote: Warnings indicate swarm design guideline violations.", file=sys.stderr)
        print("      Use --strict flag to treat warnings as errors.", file=sys.stderr)

    print(f"\nSwarm validation FAILED ({len(result.errors)} errors).", file=sys.stderr)
