#!/usr/bin/env python3
"""
mk_flow_link.py - Generate Flow Studio deep links for specific views.

This tool generates URLs that navigate Flow Studio to specific run/flow/step
combinations, making it easy to share deep links to artifacts and flow states.

Usage:
    # Basic run link
    uv run swarm/tools/mk_flow_link.py --run health-check

    # Specific flow in operator mode
    uv run swarm/tools/mk_flow_link.py --run pr-123 --flow build --mode operator

    # Step-level link with artifact view
    uv run swarm/tools/mk_flow_link.py --run abc --flow gate --step merge_decision --view artifacts --tab run

    # JSON output for programmatic use
    uv run swarm/tools/mk_flow_link.py --run abc --flow build --json

Deep link format:
    http://localhost:5000/?mode=X&run=Y&flow=Z&step=S&view=V&tab=T

Parameters:
    --run (required): Run ID (e.g., health-check, pr-123)
    --flow (optional): Flow key (signal, plan, build, gate, deploy, wisdom)
    --step (optional): Step ID within flow (e.g., self_review, merge_decision)
    --mode (optional): author | operator (default: author)
    --view (optional): spec | artifacts (default: spec)
    --tab (optional): details | run | compare
    --host (optional): Base URL (default: http://localhost:5000)
    --json (optional): Output as JSON object instead of plain URL

Examples:
    uv run swarm/tools/mk_flow_link.py --run health-check
    # → http://localhost:5000/?run=health-check

    uv run swarm/tools/mk_flow_link.py --run pr-123 --flow build --mode operator
    # → http://localhost:5000/?mode=operator&run=pr-123&flow=build

    uv run swarm/tools/mk_flow_link.py --run abc --flow gate --step merge_decision --view artifacts
    # → http://localhost:5000/?run=abc&flow=gate&step=merge_decision&view=artifacts
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

# Add repo root to path for imports
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from swarm.config.flow_registry import get_flow_keys  # noqa: E402
from swarm.utils.yaml_utils import load_yaml  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
FLOW_CONFIG_DIR = REPO_ROOT / "swarm" / "config" / "flows"
RUNS_DIR = REPO_ROOT / "swarm" / "runs"
EXAMPLES_DIR = REPO_ROOT / "swarm" / "examples"

VALID_MODES = ["author", "operator"]
VALID_VIEWS = ["spec", "artifacts"]
VALID_TABS = ["details", "run", "compare"]


# ---------------------------------------------------------------------------
# Flow Configuration Loading
# ---------------------------------------------------------------------------


@dataclass
class FlowConfig:
    """Minimal flow configuration for validation."""

    key: str
    title: str
    steps: List[str]


def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML file safely."""
    text = path.read_text(encoding="utf-8")
    data = load_yaml(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict at top level in {path}, got {type(data)}")
    return data


def load_flow_configs() -> Dict[str, FlowConfig]:
    """Load all flow configurations from swarm/config/flows/*.yaml."""
    flows: Dict[str, FlowConfig] = {}

    if not FLOW_CONFIG_DIR.exists():
        return flows

    for cfg_path in sorted(FLOW_CONFIG_DIR.glob("*.yaml")):
        try:
            data = _safe_load_yaml(cfg_path)
            key = data.get("key")
            if not key:
                continue

            # Extract step IDs
            steps_data = data.get("steps", [])
            step_ids = [
                step.get("id") for step in steps_data if isinstance(step, dict) and step.get("id")
            ]

            flows[key] = FlowConfig(
                key=key,
                title=data.get("title", ""),
                steps=step_ids,
            )
        except Exception as e:
            print(f"Warning: Failed to load flow config from {cfg_path}: {e}", file=sys.stderr)
            continue

    return flows


# ---------------------------------------------------------------------------
# Link Generator
# ---------------------------------------------------------------------------


@dataclass
class LinkResult:
    """Result of link generation."""

    url: str
    params: Dict[str, str]
    valid: bool
    warnings: List[str]


class FlowStudioLinkGenerator:
    """Generate Flow Studio deep links with validation."""

    def __init__(self, host: str = "http://localhost:5000"):
        self.host = host.rstrip("/")
        self.flows = load_flow_configs()

    def generate(
        self,
        run: str,
        flow: Optional[str] = None,
        step: Optional[str] = None,
        mode: Optional[str] = None,
        view: Optional[str] = None,
        tab: Optional[str] = None,
    ) -> LinkResult:
        """
        Generate a Flow Studio deep link.

        Args:
            run: Run ID (required)
            flow: Flow key (optional)
            step: Step ID within flow (optional)
            mode: author | operator (optional)
            view: spec | artifacts (optional)
            tab: details | run | compare (optional)

        Returns:
            LinkResult with URL, params, validity, and warnings
        """
        warnings: List[str] = []
        valid = True

        # Build query parameters (only include non-None values)
        params: Dict[str, str] = {}

        if mode:
            if mode not in VALID_MODES:
                warnings.append(f"Invalid mode '{mode}'; valid values: {', '.join(VALID_MODES)}")
                valid = False
            else:
                params["mode"] = mode

        params["run"] = run

        # Check if run exists locally (warning only, not an error)
        run_path_active = RUNS_DIR / run
        run_path_example = EXAMPLES_DIR / run
        if not run_path_active.exists() and not run_path_example.exists():
            warnings.append(f"Run '{run}' not found in swarm/runs/ or swarm/examples/")

        if flow:
            if flow not in self.flows:
                warnings.append(
                    f"Unknown flow '{flow}'; valid flows: {', '.join(sorted(self.flows.keys()))}"
                )
                valid = False
            else:
                params["flow"] = flow

                # Validate step if provided
                if step:
                    flow_config = self.flows[flow]
                    if step not in flow_config.steps:
                        warnings.append(
                            f"Step '{step}' not found in flow '{flow}'; "
                            f"valid steps: {', '.join(flow_config.steps)}"
                        )
                        valid = False
                    else:
                        params["step"] = step
        elif step:
            warnings.append("Cannot specify --step without --flow")
            valid = False

        if view:
            if view not in VALID_VIEWS:
                warnings.append(f"Invalid view '{view}'; valid values: {', '.join(VALID_VIEWS)}")
                valid = False
            else:
                params["view"] = view

        if tab:
            if tab not in VALID_TABS:
                warnings.append(f"Invalid tab '{tab}'; valid values: {', '.join(VALID_TABS)}")
                valid = False
            else:
                params["tab"] = tab

        # Build URL
        query_string = urlencode(params)
        url = f"{self.host}/?{query_string}" if query_string else self.host

        return LinkResult(
            url=url,
            params=params,
            valid=valid,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Flow Studio deep links",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --run health-check
  %(prog)s --run pr-123 --flow build --mode operator
  %(prog)s --run abc --flow gate --step merge_decision --view artifacts
  %(prog)s --run abc --flow build --json
        """,
    )

    parser.add_argument(
        "--run",
        required=True,
        help="Run ID (e.g., health-check, pr-123)",
    )
    parser.add_argument(
        "--flow",
        choices=get_flow_keys(),
        help="Flow key",
    )
    parser.add_argument(
        "--step",
        help="Step ID within flow",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        help="View mode (default: author)",
    )
    parser.add_argument(
        "--view",
        choices=VALID_VIEWS,
        help="View type (default: spec)",
    )
    parser.add_argument(
        "--tab",
        choices=VALID_TABS,
        help="Tab to display",
    )
    parser.add_argument(
        "--host",
        default="http://localhost:5000",
        help="Base URL (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON object",
    )

    args = parser.parse_args()

    # Generate link
    generator = FlowStudioLinkGenerator(host=args.host)
    result = generator.generate(
        run=args.run,
        flow=args.flow,
        step=args.step,
        mode=args.mode,
        view=args.view,
        tab=args.tab,
    )

    # Print warnings to stderr
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    # Output result
    if args.json:
        output = {
            "url": result.url,
            "params": result.params,
            "valid": result.valid,
            "warnings": result.warnings,
        }
        print(json.dumps(output, indent=2))
    else:
        print(result.url)

    # Exit with appropriate code
    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
