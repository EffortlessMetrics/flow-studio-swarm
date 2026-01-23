#!/usr/bin/env python3
"""
UX Review Orchestrator

Coordinates the UX Critic -> UX Implementer workflow for Flow Studio screens.

This script:
1. Picks a screen_id from the layout spec
2. Generates a critique prompt for the UX Critic agent
3. Generates an implementation prompt for the UX Implementer agent
4. Writes artifacts to swarm/runs/ux-review/<timestamp>/

Usage:
    # List available screens
    uv run python -m swarm.tools.ux_orchestrator --list-screens

    # Generate prompts for a specific screen
    uv run python -m swarm.tools.ux_orchestrator --screen flows.default

    # Generate prompts for all screens
    uv run python -m swarm.tools.ux_orchestrator --all

The output prompts can be fed to Claude Code agents.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).resolve().parents[2]
UX_REVIEW_DIR = REPO_ROOT / "swarm" / "runs" / "ux-review"
FLOW_STUDIO_BASE_URL = "http://localhost:5000"


# ============================================================================
# Layout Screen Fetching
# ============================================================================


def fetch_layout_screens() -> list[dict[str, Any]]:
    """Fetch layout screens from the Flow Studio API."""
    if httpx is None:
        print("ERROR: httpx required. Install with: uv add httpx", file=sys.stderr)
        sys.exit(1)

    try:
        with httpx.Client() as client:
            resp = client.get(f"{FLOW_STUDIO_BASE_URL}/api/layout_screens", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("screens", [])
    except httpx.ConnectError:
        print(
            f"ERROR: Could not connect to Flow Studio at {FLOW_STUDIO_BASE_URL}",
            file=sys.stderr,
        )
        print("       Start Flow Studio with: make flow-studio", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to fetch layout screens: {e}", file=sys.stderr)
        sys.exit(1)

    return []


def list_screen_ids() -> list[str]:
    """Get list of available screen IDs."""
    screens = fetch_layout_screens()
    return [s.get("id", "") for s in screens if s.get("id")]


# ============================================================================
# Prompt Generation
# ============================================================================


def generate_critic_prompt(screen_id: str) -> str:
    """Generate the user prompt for the UX Critic agent."""
    return f'''You are connected to the `ux_spec` and `ux_review` MCP servers.

Target screen: `"{screen_id}"`.

1. Use `ux_spec.get_layout_screen` to inspect the layout and regions for this screen.
2. Use `ux_review.run_layout_review` (with `reuse_last: true`) and then `ux_review.get_screen_snapshot` for this screen to inspect the DOM, state, graph, and screenshot.
3. Based on those, produce a **single JSON object** that conforms to `swarm/schemas/ux_critique.schema.json`, with:
   - A short `summary`.
   - A list of up to 10 `issues`, each tied to a `region` and `severity`.
   - `suggested_changes` with likely file paths where possible.

Remember: **do not** propose changes to the existing SDK fields, `data-uiid` values, or `data-ui-ready` semantics.'''


def generate_implementer_prompt(critique_json: str) -> str:
    """Generate the user prompt for the UX Implementer agent."""
    return f"""You are connected to the `ux_repo` MCP server.

Here is a UX critique object for a single screen:

```json
{critique_json}
```

1. Inspect the critique and choose a **small, coherent subset** of issues to address in a single patch (for example, all `"accessibility"` issues with `"severity": "medium"`).
2. Use `ux_repo.get_write_allowlist` and only modify files that are allowed.
3. Use `ux_repo.read_file` / `write_file` to implement the changes.
4. Run `ux_repo.run_ux_tests` and ensure tests pass, or explain clearly if they do not.
5. Respond with a **single JSON object** with the shape described in your system instructions: `summary`, `touched_files`, `pr_title`, `pr_body`, and optionally `remaining_issues`."""


# ============================================================================
# Artifact Writing
# ============================================================================


def create_run_directory(screen_id: str) -> Path:
    """Create a timestamped run directory for this review."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = UX_REVIEW_DIR / timestamp / screen_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_prompts(screen_id: str) -> dict[str, Any]:
    """Write critic and implementer prompts to the run directory."""
    run_dir = create_run_directory(screen_id)

    critic_prompt = generate_critic_prompt(screen_id)
    implementer_prompt_template = generate_implementer_prompt("<PASTE CRITIQUE JSON HERE>")

    # Write critic prompt
    critic_path = run_dir / "critic_prompt.md"
    critic_path.write_text(critic_prompt, encoding="utf-8")

    # Write implementer prompt template
    implementer_path = run_dir / "implementer_prompt_template.md"
    implementer_path.write_text(implementer_prompt_template, encoding="utf-8")

    # Write metadata
    metadata = {
        "screen_id": screen_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "critic_prompt_path": str(critic_path.relative_to(REPO_ROOT)),
        "implementer_prompt_path": str(implementer_path.relative_to(REPO_ROOT)),
    }
    metadata_path = run_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "screen_id": screen_id,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
        "critic_prompt_path": str(critic_path.relative_to(REPO_ROOT)),
        "implementer_prompt_path": str(implementer_path.relative_to(REPO_ROOT)),
    }


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UX Review Orchestrator - generate prompts for UX Critic/Implementer workflow"
    )
    parser.add_argument(
        "--list-screens",
        action="store_true",
        help="List available screen IDs from the layout spec",
    )
    parser.add_argument(
        "--screen",
        type=str,
        help="Generate prompts for a specific screen ID",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate prompts for all screens",
    )
    parser.add_argument(
        "--print-critic",
        action="store_true",
        help="Print the critic prompt to stdout (use with --screen)",
    )
    parser.add_argument(
        "--print-implementer",
        action="store_true",
        help="Print the implementer prompt template to stdout (use with --screen)",
    )

    args = parser.parse_args()

    if args.list_screens:
        screens = list_screen_ids()
        if screens:
            print("Available screens:")
            for screen_id in screens:
                print(f"  - {screen_id}")
        else:
            print("No screens found. Is Flow Studio running?")
        return 0

    if args.print_critic and args.screen:
        print(generate_critic_prompt(args.screen))
        return 0

    if args.print_implementer and args.screen:
        print(generate_implementer_prompt("<PASTE CRITIQUE JSON HERE>"))
        return 0

    if args.screen:
        result = write_prompts(args.screen)
        print(f"Created prompts for screen: {result['screen_id']}")
        print(f"  Run directory: {result['run_dir']}")
        print(f"  Critic prompt: {result['critic_prompt_path']}")
        print(f"  Implementer prompt: {result['implementer_prompt_path']}")
        return 0

    if args.all:
        screens = list_screen_ids()
        if not screens:
            print("No screens found. Is Flow Studio running?")
            return 1

        print(f"Generating prompts for {len(screens)} screens...")
        for screen_id in screens:
            result = write_prompts(screen_id)
            print(f"  - {screen_id}: {result['run_dir']}")
        print("Done.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
