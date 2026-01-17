# swarm/tools/validation/cli.py
"""CLI entrypoint for swarm validation."""

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from swarm.tools.validation.constants import (
    EXIT_SUCCESS,
    EXIT_VALIDATION_FAILED,
    EXIT_FATAL_ERROR,
)
from swarm.tools.validation.registry import parse_agents_registry
from swarm.tools.validation.reporting import (
    build_report_json,
    build_report_markdown,
    print_json_output,
    print_success,
    print_errors,
)
from swarm.tools.validation.validators.flows import parse_flow_config
from swarm.tools.validation.runner import run_validation


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Swarm alignment validator - validate spec/implementation alignment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0 - All validation checks passed
  1 - Validation failed (spec/implementation misalignment)
  2 - Fatal error (missing required files, parse errors)

Examples:
  uv run swarm/tools/validate_swarm.py
  uv run swarm/tools/validate_swarm.py --check-modified
  uv run swarm/tools/validate_swarm.py --flows-only
  uv run swarm/tools/validate_swarm.py --debug
        """
    )

    parser.add_argument(
        "--check-modified",
        action="store_true",
        help="Only check files modified vs main branch (git-aware mode)"
    )

    parser.add_argument(
        "--flows-only",
        action="store_true",
        help="Only run flow validation checks (skip agent/adapter validation)"
    )

    parser.add_argument(
        "--check-prompts",
        action="store_true",
        help="Validate agent prompt sections (## Inputs, ## Outputs, ## Behavior)"
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce swarm design constraints (tools/permissionMode become errors, not warnings)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output with timing and validation steps"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON with detailed per-agent/flow/step results"
    )

    parser.add_argument(
        "--report",
        choices=["json", "markdown"],
        help="Output format for validation report (json or markdown)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="validate_swarm.py 2.1.0"
    )

    args = parser.parse_args()

    # Parse registry first (needed for both validation and JSON output)
    try:
        registry = parse_agents_registry()
    except SystemExit:
        if args.json:
            error_output: Dict[str, Any] = {
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "summary": {"status": "ERROR", "message": "Failed to parse agent registry"},
                "agents": {},
                "flows": {},
                "steps": {},
                "errors": [],
                "warnings": [],
            }
            print(json.dumps(error_output, indent=2))
        raise

    # Run validation
    try:
        result = run_validation(
            check_modified=args.check_modified,
            debug=args.debug,
            strict_mode=args.strict,
            flows_only=args.flows_only,
            check_prompts=args.check_prompts
        )
    except SystemExit:
        raise
    except Exception as e:
        if args.json:
            error_output = {
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "summary": {"status": "ERROR", "message": f"Unexpected error: {e}"},
                "agents": {},
                "flows": {},
                "steps": {},
                "errors": [],
                "warnings": [],
            }
            print(json.dumps(error_output, indent=2))
            sys.exit(EXIT_FATAL_ERROR)
        print(f"ERROR: Unexpected error during validation: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc(file=sys.stderr)
        sys.exit(EXIT_FATAL_ERROR)

    # Report results
    if args.report == "json":
        # Simplified FR-012 JSON report format
        report = build_report_json(result)
        print(json.dumps(report, indent=2))
        sys.exit(EXIT_SUCCESS if not result.has_errors() else EXIT_VALIDATION_FAILED)
    elif args.report == "markdown":
        # Markdown report format
        report = build_report_markdown(result)
        print(report)
        sys.exit(EXIT_SUCCESS if not result.has_errors() else EXIT_VALIDATION_FAILED)
    elif args.json:
        # Detailed JSON output mode - print structured JSON to stdout
        print_json_output(result, registry, parse_flow_config)
        sys.exit(EXIT_SUCCESS if not result.has_errors() else EXIT_VALIDATION_FAILED)
    elif result.has_errors():
        print_errors(result)
        sys.exit(EXIT_VALIDATION_FAILED)
    else:
        print_success(result)
        sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
