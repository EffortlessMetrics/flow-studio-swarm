"""
Command-line interface for selftest-core.

This module provides the CLI entry point for running selftest from
the command line.

Usage:
    selftest run                     # Run all steps (strict mode)
    selftest run --degraded          # Degraded mode (only KERNEL failures block)
    selftest run --kernel-only       # Run only KERNEL tier steps
    selftest run --step lint         # Run specific step
    selftest plan                    # Show execution plan
    selftest doctor                  # Run diagnostics
    selftest --version               # Show version
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_config, load_steps_from_yaml
from .doctor import SelfTestDoctor
from .reporter import ConsoleReporter, ReportGenerator
from .runner import SelfTestRunner, Step


def find_config_file() -> Path | None:
    """Find selftest configuration file in common locations."""
    candidates = [
        Path("selftest.yaml"),
        Path("selftest.yml"),
        Path(".selftest.yaml"),
        Path(".selftest.yml"),
        Path("selftest_config.yaml"),
        Path("selftest_config.yml"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_steps_from_config() -> list[Step]:
    """Load steps from configuration file if present."""
    config_file = find_config_file()
    if config_file:
        return load_steps_from_yaml(config_file)
    return []


def cmd_run(args: argparse.Namespace) -> int:
    """Run selftest steps."""
    # Load configuration
    if args.config:
        config = load_config(args.config)
        steps = config.steps
    else:
        steps = load_steps_from_config()

    if not steps:
        print("Error: No steps configured.", file=sys.stderr)
        print(
            "Create a selftest.yaml file or use --config to specify one.",
            file=sys.stderr,
        )
        return 2

    # Determine mode
    if args.kernel_only:
        mode = "kernel-only"
    elif args.degraded:
        mode = "degraded"
    else:
        mode = "strict"

    # Filter to specific step if requested
    if args.step:
        step_ids = {s.id for s in steps}
        if args.step not in step_ids:
            print(f"Error: Unknown step '{args.step}'", file=sys.stderr)
            print(f"Available steps: {', '.join(sorted(step_ids))}", file=sys.stderr)
            return 2
        steps = [s for s in steps if s.id == args.step]

    # Create runner with callbacks for progress
    def on_step_start(step: Step):
        if not args.json:
            print(f"RUN  {step.id:30s} ... ", end="", flush=True)

    def on_step_complete(step: Step, result):
        if not args.json:
            status = result.status
            duration = result.duration_ms
            print(f"{status} ({duration}ms)")

    runner = SelfTestRunner(
        steps=steps,
        mode=mode,
        verbose=args.verbose,
        on_step_start=on_step_start,
        on_step_complete=on_step_complete,
    )

    # Run selftest
    result = runner.run()

    # Output results
    if args.json:
        generator = ReportGenerator(result)
        print(generator.to_json(version="v2" if args.json_v2 else "v1"))
    else:
        reporter = ConsoleReporter(result, verbose=args.verbose)
        reporter.print_summary()
        reporter.print_severity_breakdown()
        reporter.print_category_breakdown()
        reporter.print_hints()

    # Write report to file if requested
    if args.report:
        generator = ReportGenerator(result)
        generator.write_json(args.report)
        if not args.json:
            print(f"\nReport written to: {args.report}")

    # Return exit code based on result
    if result["status"] == "PASS":
        return 0
    return 1


def cmd_plan(args: argparse.Namespace) -> int:
    """Show execution plan."""
    # Load configuration
    if args.config:
        config = load_config(args.config)
        steps = config.steps
    else:
        steps = load_steps_from_config()

    if not steps:
        print("Error: No steps configured.", file=sys.stderr)
        return 2

    # Determine mode
    if args.kernel_only:
        mode = "kernel-only"
    else:
        mode = "strict"

    runner = SelfTestRunner(steps=steps, mode=mode)
    plan = runner.plan()

    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print("=" * 70)
        print("SELFTEST PLAN")
        print("=" * 70)
        print()
        for i, step in enumerate(plan["steps"], 1):
            tier = step["tier"].upper()
            severity = step["severity"].upper()
            category = step["category"].upper()
            deps = ""
            if step["dependencies"]:
                deps = f" (depends: {', '.join(step['dependencies'])})"
            print(
                f"[{i}] {step['id']:20s} [{tier:10s}] [{severity:8s}] "
                f"[{category:12s}] {step['description']}{deps}"
            )
        print()
        summary = plan["summary"]
        print(f"Total steps: {summary['total']}")
        print(f"  KERNEL:     {summary['by_tier']['kernel']}")
        print(f"  GOVERNANCE: {summary['by_tier']['governance']}")
        print(f"  OPTIONAL:   {summary['by_tier']['optional']}")

    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run diagnostics."""
    doctor = SelfTestDoctor()
    diagnosis = doctor.diagnose()

    if args.json:
        print(json.dumps(diagnosis, indent=2))
    else:
        doctor.print_diagnosis(diagnosis)

    # Return code based on diagnosis
    if diagnosis["summary"] == "HEALTHY":
        return 0
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    """List available steps."""
    # Load configuration
    if args.config:
        config = load_config(args.config)
        steps = config.steps
    else:
        steps = load_steps_from_config()

    if not steps:
        print("No steps configured.", file=sys.stderr)
        return 0

    print("Available steps:")
    for step in steps:
        tier = step.tier.value.upper()
        print(f"  {step.id:25s} [{tier:10s}] {step.description}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="selftest",
        description="Layered selftest governance framework",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"selftest-core {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run selftest steps")
    run_parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file",
    )
    run_parser.add_argument(
        "--degraded",
        action="store_true",
        help="Degraded mode: only KERNEL failures block",
    )
    run_parser.add_argument(
        "--kernel-only",
        action="store_true",
        help="Run only KERNEL tier steps",
    )
    run_parser.add_argument(
        "--step",
        type=str,
        help="Run only the specified step",
    )
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    run_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON report",
    )
    run_parser.add_argument(
        "--json-v2",
        action="store_true",
        help="Output JSON v2 report with full metadata",
    )
    run_parser.add_argument(
        "--report",
        type=str,
        help="Write JSON report to file",
    )

    # Plan command
    plan_parser = subparsers.add_parser("plan", help="Show execution plan")
    plan_parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file",
    )
    plan_parser.add_argument(
        "--kernel-only",
        action="store_true",
        help="Show only KERNEL tier steps",
    )
    plan_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON plan",
    )

    # Doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Run diagnostics")
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON diagnostics",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List available steps")
    list_parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "run":
        return cmd_run(args)
    elif args.command == "plan":
        return cmd_plan(args)
    elif args.command == "doctor":
        return cmd_doctor(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
