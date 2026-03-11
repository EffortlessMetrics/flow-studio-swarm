#!/usr/bin/env python3
"""
Stepwise Resume Tool (v2.4.0)

Resume a stepwise run from a specific step or the last successful checkpoint.

Usage:
    uv run swarm/tools/stepwise_resume.py <run_id> --from-step <step_id>
    uv run swarm/tools/stepwise_resume.py <run_id> --from-last-success
    uv run swarm/tools/stepwise_resume.py <run_id> --from-step <step_id> --dry-run

Examples:
    # Resume from specific step
    uv run swarm/tools/stepwise_resume.py run-abc123 --from-step critique_tests

    # Resume from last successful step
    uv run swarm/tools/stepwise_resume.py run-abc123 --from-last-success

    # Preview what would happen
    uv run swarm/tools/stepwise_resume.py run-abc123 --from-step critique_tests --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add repo root to path for imports
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from swarm.runtime.safe_paths import validate_path_component

def find_run_path(run_id: str) -> Optional[Path]:
    """Find the path to a run directory.

    Searches in order:
    1. swarm/runs/<run_id>/
    2. swarm/examples/<run_id>/

    Args:
        run_id: The run identifier

    Returns:
        Path to run directory, or None if not found
    """
    validate_path_component(run_id, "run_id")

    runs_path = _REPO_ROOT / "swarm" / "runs" / run_id
    if runs_path.exists():
        return runs_path

    examples_path = _REPO_ROOT / "swarm" / "examples" / run_id
    if examples_path.exists():
        return examples_path

    return None


def read_events(run_path: Path) -> List[Dict[str, Any]]:
    """Read events from a run's events.jsonl file.

    Args:
        run_path: Path to the run directory

    Returns:
        List of event dictionaries
    """
    events_path = run_path / "events.jsonl"
    if not events_path.exists():
        return []

    events = []
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def read_spec(run_path: Path) -> Optional[Dict[str, Any]]:
    """Read the run spec from spec.json.

    Args:
        run_path: Path to the run directory

    Returns:
        Run spec dictionary, or None if not found
    """
    spec_path = run_path / "spec.json"
    if not spec_path.exists():
        return None

    with spec_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_last_successful_step(events: List[Dict[str, Any]]) -> Optional[str]:
    """Find the last successfully completed step in a run.

    Reads events and finds the last step_end event with success status.

    Args:
        events: List of event dictionaries

    Returns:
        Step ID of last successful step, or None if no successful steps
    """
    last_success = None

    for event in events:
        kind = event.get("kind", "")
        if kind == "step_end":
            step_id = event.get("step_id")
            status = event.get("payload", {}).get("status", "")
            if step_id and status in ("success", "completed"):
                last_success = step_id

    return last_success


def get_all_steps(run_path: Path, spec: Dict[str, Any]) -> List[Dict[str, str]]:
    """Get all steps for a run based on its spec.

    Args:
        run_path: Path to the run directory
        spec: Run specification

    Returns:
        List of step info dicts with flow_key, step_id, agents
    """
    from swarm.config.flow_registry import FlowRegistry

    registry = FlowRegistry.get_instance()
    steps = []

    flow_keys = spec.get("flow_keys", [])
    for flow_key in flow_keys:
        flow = registry.get_flow(flow_key)
        if not flow:
            continue

        for step in flow.steps:
            steps.append(
                {
                    "flow_key": flow_key,
                    "step_id": step.id,
                    "agents": ", ".join(step.agents),
                    "role": step.role,
                }
            )

    return steps


def print_execution_plan(run_id: str, run_path: Path, spec: Dict[str, Any], from_step: str) -> None:
    """Print what would be executed in a resume (dry-run mode).

    Args:
        run_id: The run identifier
        run_path: Path to the run directory
        spec: Run specification
        from_step: Step ID to resume from
    """
    steps = get_all_steps(run_path, spec)

    print(f"\n{'=' * 60}")
    print(f"Resume Plan for: {run_id}")
    print(f"{'=' * 60}")
    print(f"Run path: {run_path}")
    print(f"Resume from step: {from_step}")
    print(f"Flows: {', '.join(spec.get('flow_keys', []))}")
    print(f"Backend: {spec.get('backend', 'unknown')}")
    print()

    found_resume_point = False
    current_flow = None

    for step in steps:
        # Print flow header when flow changes
        if step["flow_key"] != current_flow:
            current_flow = step["flow_key"]
            print(f"\nFlow: {current_flow}")
            print("-" * 40)

        # Check if this is the resume point
        if step["step_id"] == from_step:
            found_resume_point = True

        status = "SKIP" if not found_resume_point else "RUN"
        status_marker = "  " if found_resume_point else "~~"

        print(f"  [{status}] {step['step_id']}")
        print(f"  {status_marker}  Role: {step['role'][:50]}...")
        print(f"  {status_marker}  Agents: {step['agents']}")

    if not found_resume_point:
        print(f"\n WARNING: Step '{from_step}' not found in flow steps!")
        print("Available steps:")
        for step in steps:
            print(f"  - {step['flow_key']}/{step['step_id']}")

    print()


def resume_run(
    run_id: str,
    from_step: Optional[str] = None,
    from_last_success: bool = False,
    dry_run: bool = False,
) -> int:
    """Resume a stepwise run from a checkpoint.

    Args:
        run_id: The run to resume
        from_step: Step ID to resume from (mutually exclusive with from_last_success)
        from_last_success: If True, find and resume from last successful step
        dry_run: If True, only print what would happen

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Validate run exists
    run_path = find_run_path(run_id)
    if not run_path:
        print(f"ERROR: Run '{run_id}' not found")
        print("Searched in:")
        print(f"  - swarm/runs/{run_id}/")
        print(f"  - swarm/examples/{run_id}/")
        return 1

    # Read spec
    spec = read_spec(run_path)
    if not spec:
        print(f"ERROR: No spec.json found for run '{run_id}'")
        return 1

    # Determine resume point
    if from_last_success:
        events = read_events(run_path)
        from_step = find_last_successful_step(events)
        if not from_step:
            print(f"ERROR: No successful steps found in run '{run_id}'")
            return 1
        print(f"Found last successful step: {from_step}")

    if not from_step:
        print("ERROR: Must specify --from-step or --from-last-success")
        return 1

    # Dry run: just print plan
    if dry_run:
        print_execution_plan(run_id, run_path, spec, from_step)
        return 0

    # TODO: Actual resume implementation
    # This requires:
    # 1. Load spec and reconstruct orchestrator
    # 2. Call run_stepwise_flow with start_step=from_step
    # 3. Handle events properly (append vs overwrite)

    print("=" * 60)
    print("Resume Execution")
    print("=" * 60)
    print()
    print("NOTE: Full resume execution not yet implemented.")
    print("This is a v2.4.0 feature. See docs/CONFIG_PHASE_1.md")
    print()
    print("For now, use --dry-run to preview the execution plan.")
    print()
    print("Workaround: Manually restart the flow with start_step parameter:")
    print("  orchestrator.run_stepwise_flow(")
    print(f"      flow_key='{spec.get('flow_keys', ['unknown'])[0]}',")
    print("      spec=spec,")
    print(f"      start_step='{from_step}'")
    print("  )")

    return 2


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Resume a stepwise run from a checkpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Resume from specific step
    uv run swarm/tools/stepwise_resume.py run-abc123 --from-step critique_tests

    # Resume from last successful step
    uv run swarm/tools/stepwise_resume.py run-abc123 --from-last-success

    # Preview what would happen
    uv run swarm/tools/stepwise_resume.py run-abc123 --from-step critique_tests --dry-run

Note:
    Full resume execution is a v2.4.0 feature. Currently only --dry-run is
    fully implemented. See docs/CONFIG_PHASE_1.md for the design document.
""",
    )

    parser.add_argument("run_id", help="Run identifier to resume")
    parser.add_argument("--from-step", help="Step ID to resume from")
    parser.add_argument(
        "--from-last-success",
        action="store_true",
        help="Resume from the last successfully completed step",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print execution plan without running"
    )

    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.from_step and args.from_last_success:
        print("ERROR: Cannot specify both --from-step and --from-last-success")
        return 1

    if not args.from_step and not args.from_last_success:
        print("ERROR: Must specify either --from-step or --from-last-success")
        parser.print_help()
        return 1

    return resume_run(
        run_id=args.run_id,
        from_step=args.from_step,
        from_last_success=args.from_last_success,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
