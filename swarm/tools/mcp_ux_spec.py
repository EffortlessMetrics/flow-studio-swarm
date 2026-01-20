#!/usr/bin/env python3
"""
MCP Server: ux_spec

Access Flow Studio UX manifest, layout spec, and governance contracts.
This server provides read-only access to the UX contract surface.

Usage (standalone):
    uv run python -m swarm.tools.mcp_ux_spec

Usage (with Claude Code):
    Add to ~/.config/claude/mcp.json:
    {
      "ux_spec": {
        "command": "uv",
        "args": ["run", "python", "-m", "swarm.tools.mcp_ux_spec"],
        "cwd": "/path/to/flow-studio"
      }
    }

Depends on:
    - ux_manifest.json (UX contract index)
    - Flow Studio API at http://localhost:5000 (for live layout screens)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None  # Optional for live API calls

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
MANIFEST_PATH = REPO_ROOT / "ux_manifest.json"
SCHEMA_PATH = REPO_ROOT / "swarm" / "schemas" / "ux_critique.schema.json"
FLOW_STUDIO_BASE_URL = "http://localhost:5000"


# ============================================================================
# Static Layout Spec Fallback (from TypeScript layout_spec.ts)
# ============================================================================

STATIC_LAYOUT_SCREENS: List[Dict[str, Any]] = [
    {
        "id": "flows.default",
        "route": "/",
        "title": "Flows - Default",
        "description": "Main Flow Studio screen with run selector, flow list, graph canvas, and inspector.",
        "purpose": "Main Flow Studio screen with run selector, flow list, graph canvas, and inspector.",
        "regions": [
            {
                "id": "header",
                "purpose": "Global navigation, search, governance indicators, mode toggle.",
                "uiids": [
                    "flow_studio.header",
                    "flow_studio.header.search",
                    "flow_studio.header.search.input",
                    "flow_studio.header.search.results",
                    "flow_studio.header.controls",
                    "flow_studio.header.tour",
                    "flow_studio.header.tour.trigger",
                    "flow_studio.header.tour.menu",
                    "flow_studio.header.mode",
                    "flow_studio.header.mode.author",
                    "flow_studio.header.mode.operator",
                    "flow_studio.header.governance",
                    "flow_studio.header.governance.overlay",
                    "flow_studio.header.reload",
                    "flow_studio.header.reload.btn",
                    "flow_studio.header.help",
                ],
            },
            {
                "id": "sdlc_bar",
                "purpose": "SDLC progress bar showing flow completion status.",
                "uiids": ["flow_studio.sdlc_bar"],
            },
            {
                "id": "sidebar",
                "purpose": "Run selector, flow list, and view toggles between agents and artifacts.",
                "uiids": [
                    "flow_studio.sidebar",
                    "flow_studio.sidebar.run_selector",
                    "flow_studio.sidebar.run_selector.select",
                    "flow_studio.sidebar.compare_selector",
                    "flow_studio.sidebar.flow_list",
                    "flow_studio.sidebar.view_toggle",
                ],
            },
            {
                "id": "canvas",
                "purpose": "Graph visualization of the current flow and SDLC legend.",
                "uiids": [
                    "flow_studio.canvas",
                    "flow_studio.canvas.graph",
                    "flow_studio.canvas.legend",
                    "flow_studio.canvas.legend.toggle",
                    "flow_studio.canvas.outline",
                ],
            },
            {
                "id": "inspector",
                "purpose": "Details panel for selected step/agent/artifact, timing, and timeline.",
                "uiids": [
                    "flow_studio.inspector",
                    "flow_studio.inspector.details",
                ],
            },
        ],
    },
    {
        "id": "flows.selftest",
        "route": "/?modal=selftest",
        "title": "Flows - Selftest Modal",
        "description": "Selftest plan / results modal and controls.",
        "purpose": "Selftest plan / results modal and controls.",
        "regions": [
            {
                "id": "modal",
                "purpose": "Selftest plan, run controls, copy helpers.",
                "uiids": ["flow_studio.modal.selftest"],
            },
        ],
    },
    {
        "id": "flows.shortcuts",
        "route": "/?modal=shortcuts",
        "title": "Flows - Shortcuts Modal",
        "description": "Keyboard shortcuts reference modal.",
        "purpose": "Keyboard shortcuts reference modal.",
        "regions": [
            {
                "id": "modal",
                "purpose": "Keyboard shortcuts grid.",
                "uiids": ["flow_studio.modal.shortcuts"],
            },
        ],
    },
    {
        "id": "flows.validation",
        "route": "/?tab=validation",
        "title": "Flows - Validation View",
        "description": "Governance validation results and FR status badges.",
        "purpose": "Governance validation results and FR status badges.",
        "regions": [
            {
                "id": "header",
                "purpose": "Governance badge and overlay toggle.",
                "uiids": [
                    "flow_studio.header.governance",
                    "flow_studio.header.governance.overlay",
                ],
            },
            {
                "id": "inspector",
                "purpose": "Validation details for selected agent or flow.",
                "uiids": [
                    "flow_studio.inspector",
                    "flow_studio.inspector.details",
                ],
            },
        ],
    },
    {
        "id": "flows.tour",
        "route": "/?tour=<tour_id>",
        "title": "Flows - Tour Mode",
        "description": "Guided tour overlay with step-by-step navigation.",
        "purpose": "Guided tour overlay with step-by-step navigation.",
        "regions": [
            {
                "id": "header",
                "purpose": "Tour menu and controls.",
                "uiids": [
                    "flow_studio.header.tour",
                    "flow_studio.header.tour.trigger",
                    "flow_studio.header.tour.menu",
                ],
            },
            {
                "id": "canvas",
                "purpose": "Tour card overlay on graph nodes.",
                "uiids": [
                    "flow_studio.canvas",
                    "flow_studio.canvas.graph",
                ],
            },
        ],
    },
]


# ============================================================================
# Core Functions
# ============================================================================

def load_ux_manifest() -> Dict[str, Any]:
    """Load the ux_manifest.json file."""
    if not MANIFEST_PATH.exists():
        return {"error": f"Manifest not found at {MANIFEST_PATH}"}
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        # Add layout_spec alias for backward compatibility
        if "specs" in manifest and "layout_spec" not in manifest:
            manifest["layout_spec"] = manifest["specs"]
        return manifest
    except Exception as e:
        return {"error": f"Failed to load manifest: {e}"}


def load_critique_schema() -> Dict[str, Any]:
    """Load the UX critique JSON schema."""
    if not SCHEMA_PATH.exists():
        return {"error": f"Schema not found at {SCHEMA_PATH}"}
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"Failed to load schema: {e}"}


def fetch_layout_screens_from_api() -> Optional[List[Dict[str, Any]]]:
    """Fetch layout screens from the live Flow Studio API."""
    if httpx is None:
        return None
    try:
        with httpx.Client() as client:
            resp = client.get(f"{FLOW_STUDIO_BASE_URL}/api/layout_screens", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Return just the screens list
                if isinstance(data, dict) and "screens" in data:
                    return data["screens"]
                elif isinstance(data, list):
                    return data
    except Exception:
        pass
    return None


def get_layout_screens() -> List[Dict[str, Any]]:
    """Get layout screens as a list.

    Prefers live API over static fallback.
    Returns list of screen dicts with id, route, regions, purpose.
    """
    # Try live API first
    live = fetch_layout_screens_from_api()
    if live:
        return live

    # Fallback to static layout spec
    return STATIC_LAYOUT_SCREENS


def get_screen_by_id(screen_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific screen from the layout spec."""
    if not screen_id:
        return None
    screens = get_layout_screens()
    for screen in screens:
        if screen.get("id") == screen_id:
            return screen
    return None


def get_all_known_uiids() -> List[str]:
    """Extract all UIIDs from the layout spec."""
    uiids = set()
    screens = get_layout_screens()
    for screen in screens:
        for region in screen.get("regions", []):
            for uiid in region.get("uiids", []):
                uiids.add(uiid)
    return sorted(uiids)


# ============================================================================
# Backward-Compatible Function Aliases (for test compatibility)
# ============================================================================

def get_ux_manifest() -> Dict[str, Any]:
    """Alias for load_ux_manifest for backward compatibility."""
    return load_ux_manifest()


def get_layout_screen_by_id(screen_id: str) -> Optional[Dict[str, Any]]:
    """Alias for get_screen_by_id for backward compatibility."""
    return get_screen_by_id(screen_id)


def get_critique_schema() -> Dict[str, Any]:
    """Alias for load_critique_schema for backward compatibility."""
    return load_critique_schema()


# ============================================================================
# MCP Server
# ============================================================================

def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("ux_spec")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="get_ux_manifest",
                description=(
                    "Return the parsed ux_manifest.json for Flow Studio UX. "
                    "This is the authoritative index of specs, docs, tests, tools, "
                    "API endpoints, SDK methods, and workflows for UX review."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_layout_screens",
                description=(
                    "Return list of layout screens and regions from the Flow Studio API. "
                    "Each screen has an id, route, title, description, and regions. "
                    "Each region has a purpose and list of UIIDs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_layout_screen",
                description=(
                    "Get a single screen's layout spec by ID. "
                    "Returns the screen's route, regions, and UIIDs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "screen_id": {
                            "type": "string",
                            "description": "Screen ID from the layout spec (e.g., 'flows.default')",
                        },
                    },
                    "required": ["screen_id"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_all_uiids",
                description=(
                    "Get all known UIIDs across all screens. "
                    "Useful for validating UIID references in critiques."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_critique_schema",
                description=(
                    "Return the JSON schema for UX critique objects. "
                    "Use this to understand the expected output format for critiques."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name == "get_ux_manifest":
            manifest = load_ux_manifest()
            return [TextContent(type="text", text=json.dumps(manifest, indent=2))]

        elif name == "get_layout_screens":
            result = get_layout_screens()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_layout_screen":
            screen_id = arguments["screen_id"]
            screen = get_screen_by_id(screen_id)
            if screen:
                return [TextContent(type="text", text=json.dumps(screen, indent=2))]
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Screen '{screen_id}' not found"}, indent=2),
            )]

        elif name == "get_all_uiids":
            uiids = get_all_known_uiids()
            return [TextContent(
                type="text",
                text=json.dumps({"uiids": uiids, "count": len(uiids)}, indent=2),
            )]

        elif name == "get_critique_schema":
            schema = load_critique_schema()
            return [TextContent(type="text", text=json.dumps(schema, indent=2))]

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
