#!/usr/bin/env python3
"""
MCP Server: ux_review

Capture and load per-screen UI review artifacts for Flow Studio.
This server wraps run_layout_review.py and provides structured access
to the captured DOM, state, and screenshot artifacts.

Usage (standalone):
    uv run python -m swarm.tools.mcp_ux_review

Usage (with Claude Code):
    Add to ~/.config/claude/mcp.json:
    {
      "ux_review": {
        "command": "uv",
        "args": ["run", "python", "-m", "swarm.tools.mcp_ux_review"],
        "cwd": "/path/to/flow-studio"
      }
    }

Depends on:
    - run_layout_review.py (for capturing artifacts)
    - Flow Studio running at http://localhost:5000 (for live captures)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# MCP protocol imports
try:
    from mcp.server import Server  # type: ignore[import-not-found]
    from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]
    from mcp.types import TextContent, Tool  # type: ignore[import-not-found]
except ImportError:
    print("ERROR: mcp package required. Install with: uv add mcp", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_REVIEW_DIR = REPO_ROOT / "swarm" / "runs" / "ui-review"


# ============================================================================
# Data Types
# ============================================================================


@dataclass
class ScreenSnapshot:
    """Captured artifacts for a single screen."""

    run_id: str
    screen_id: str
    route: str = ""
    dom_html: Optional[str] = None
    state_json: Optional[Dict[str, Any]] = None
    graph_json: Optional[Dict[str, Any]] = None
    screenshot_path: Optional[str] = None
    screen_spec: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "screen_id": self.screen_id,
            "route": self.route,
            "dom_html": self.dom_html,
            "state": self.state_json,
            "graph": self.graph_json,
            "screenshot_path": self.screenshot_path,
            "screen_spec": self.screen_spec,
            "errors": self.errors,
        }


@dataclass
class ReviewRun:
    """Summary of a layout review run."""

    run_id: str
    timestamp: str
    base_url: str
    screens: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "base_url": self.base_url,
            "screens": self.screens,
        }


# ============================================================================
# Core Functions
# ============================================================================


def list_review_runs() -> List[str]:
    """List all available review run IDs (timestamps)."""
    if not UI_REVIEW_DIR.exists():
        return []
    return sorted(
        [d.name for d in os.scandir(UI_REVIEW_DIR) if d.is_dir()],
        reverse=True,  # Most recent first
    )


def get_latest_run_id() -> Optional[str]:
    """Get the most recent run ID."""
    runs = list_review_runs()
    return runs[0] if runs else None


def load_review_summary(run_id: str) -> Optional[ReviewRun]:
    """Load the summary.json for a review run."""
    summary_path = UI_REVIEW_DIR / run_id / "summary.json"
    if not summary_path.exists():
        return None

    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return ReviewRun(
            run_id=data.get("run_id", run_id),
            timestamp=data.get("timestamp", ""),
            base_url=data.get("base_url", ""),
            screens=data.get("screens", []),
        )
    except Exception:
        return None


def load_screen_snapshot(run_id: str, screen_id: str) -> ScreenSnapshot:
    """Load all captured artifacts for a specific screen."""
    snapshot = ScreenSnapshot(run_id=run_id, screen_id=screen_id)
    screen_dir = UI_REVIEW_DIR / run_id / screen_id

    if not screen_dir.exists():
        snapshot.errors.append(f"Screen directory not found: {screen_dir}")
        return snapshot

    # Load DOM HTML
    dom_path = screen_dir / "dom.html"
    if dom_path.exists():
        try:
            snapshot.dom_html = dom_path.read_text(encoding="utf-8")
        except Exception as e:
            snapshot.errors.append(f"Failed to read dom.html: {e}")

    # Load state JSON
    state_path = screen_dir / "state.json"
    if state_path.exists():
        try:
            snapshot.state_json = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as e:
            snapshot.errors.append(f"Failed to read state.json: {e}")

    # Load graph JSON (if present)
    graph_path = screen_dir / "graph.json"
    if graph_path.exists():
        try:
            snapshot.graph_json = json.loads(graph_path.read_text(encoding="utf-8"))
        except Exception as e:
            snapshot.errors.append(f"Failed to read graph.json: {e}")

    # Check for screenshot
    screenshot_path = screen_dir / "screenshot.png"
    if screenshot_path.exists():
        snapshot.screenshot_path = str(screenshot_path)

    # Load screen spec
    spec_path = screen_dir / "screen_spec.json"
    if spec_path.exists():
        try:
            snapshot.screen_spec = json.loads(spec_path.read_text(encoding="utf-8"))
            snapshot.route = snapshot.screen_spec.get("route", "")
        except Exception as e:
            snapshot.errors.append(f"Failed to read screen_spec.json: {e}")

    return snapshot


def run_layout_review_script() -> Dict[str, Any]:
    """Execute run_layout_review.py and return the result."""
    script_path = REPO_ROOT / "swarm" / "tools" / "run_layout_review.py"

    try:
        result = subprocess.run(
            ["uv", "run", str(script_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )

        success = result.returncode == 0

        # Find the newly created run
        latest_run = get_latest_run_id()
        summary = load_review_summary(latest_run) if latest_run else None

        return {
            "success": success,
            "run_id": latest_run,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "summary": summary.to_dict() if summary else None,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Layout review timed out (120s limit)",
            "run_id": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "run_id": None,
        }


# ============================================================================
# MCP Server
# ============================================================================


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("ux_review")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="run_layout_review",
                description=(
                    "Run the layout review script to capture DOM, state, and screenshots "
                    "for all Flow Studio screens. Returns the run ID and summary. "
                    "Use reuse_last=true to skip capture if a recent run exists."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reuse_last": {
                            "type": "boolean",
                            "default": True,
                            "description": (
                                "If true and a recent run exists, return that instead of "
                                "capturing new artifacts. Set to false to force a fresh capture."
                            ),
                        },
                    },
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="list_review_runs",
                description=(
                    "List all available review runs (timestamps). "
                    "Returns run IDs sorted by most recent first."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_screen_snapshot",
                description=(
                    "Load captured artifacts (DOM, state, screenshot) for a specific screen "
                    "from a review run. Use this to examine the current state of a Flow Studio screen."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "Timestamp folder name under swarm/runs/ui-review",
                        },
                        "screen_id": {
                            "type": "string",
                            "description": "Screen ID from the layout spec (e.g., 'flows.default')",
                        },
                    },
                    "required": ["run_id", "screen_id"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_run_summary",
                description=(
                    "Get the summary for a specific review run, including list of screens "
                    "and their capture status."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "Timestamp folder name under swarm/runs/ui-review",
                        },
                    },
                    "required": ["run_id"],
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name == "run_layout_review":
            reuse_last = arguments.get("reuse_last", True)

            # Check for existing run if reuse_last
            if reuse_last:
                latest = get_latest_run_id()
                if latest:
                    summary = load_review_summary(latest)
                    if summary:
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {
                                        "reused": True,
                                        "run_id": latest,
                                        "summary": summary.to_dict(),
                                    },
                                    indent=2,
                                ),
                            )
                        ]

            # Run fresh capture
            result = run_layout_review_script()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "list_review_runs":
            runs = list_review_runs()
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"runs": runs}, indent=2),
                )
            ]

        elif name == "get_screen_snapshot":
            run_id = arguments["run_id"]
            screen_id = arguments["screen_id"]
            snapshot = load_screen_snapshot(run_id, screen_id)

            # Truncate DOM if too large (> 50KB)
            result = snapshot.to_dict()
            if result.get("dom_html") and len(result["dom_html"]) > 50000:
                result["dom_html"] = result["dom_html"][:50000] + "\n<!-- TRUNCATED -->"
                result["dom_truncated"] = True

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_run_summary":
            run_id = arguments["run_id"]
            summary = load_review_summary(run_id)
            if summary:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(summary.to_dict(), indent=2),
                    )
                ]
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Run '{run_id}' not found"}, indent=2),
                )
            ]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    return server


async def main():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
