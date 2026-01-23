#!/usr/bin/env python3
"""
MCP Server: ux_repo

Read/write Flow Studio code and run UX-related tests.
This server provides governed file access for the UX improvement workflow.

Usage (standalone):
    uv run python -m swarm.tools.mcp_ux_repo

Usage (with Claude Code):
    Add to ~/.config/claude/mcp.json:
    {
      "ux_repo": {
        "command": "uv",
        "args": ["run", "python", "-m", "swarm.tools.mcp_ux_repo"],
        "cwd": "/path/to/flow-studio"
      }
    }

Governed Allowlist:
    - swarm/tools/flow_studio_ui/src/**
    - swarm/tools/flow_studio_ui/css/**
    - docs/FLOW_STUDIO*.md
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

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

# Governed file patterns - only these can be written
WRITE_ALLOWLIST_PATTERNS = [
    r"^swarm/tools/flow_studio_ui/src/.*\.ts$",
    r"^swarm/tools/flow_studio_ui/css/.*\.css$",
    r"^docs/FLOW_STUDIO.*\.md$",
]

# Patterns that require extra caution (governed surfaces)
GOVERNED_SURFACE_PATTERNS = [
    r"FlowStudioSDK",
    r"FlowStudioUIID",
    r"data-ui-ready",
    r"data-uiid",
    r"window\.__flowStudio",
]


# ============================================================================
# Core Functions
# ============================================================================


def is_path_allowed(path: str) -> bool:
    """Check if a path matches the write allowlist."""
    for pattern in WRITE_ALLOWLIST_PATTERNS:
        if re.match(pattern, path):
            return True
    return False


def detect_governed_changes(old_content: str, new_content: str) -> List[str]:
    """Detect if changes touch governed surfaces."""
    warnings = []
    for pattern in GOVERNED_SURFACE_PATTERNS:
        old_matches = len(re.findall(pattern, old_content))
        new_matches = len(re.findall(pattern, new_content))
        if old_matches != new_matches:
            warnings.append(
                f"Governed surface '{pattern}' count changed: {old_matches} -> {new_matches}"
            )
    return warnings


def read_file(path: str) -> Dict[str, Any]:
    """Read a file from the repo."""
    full_path = REPO_ROOT / path
    if not full_path.exists():
        return {"error": f"File not found: {path}"}

    try:
        content = full_path.read_text(encoding="utf-8")
        return {
            "path": path,
            "content": content,
            "size": len(content),
            "lines": len(content.splitlines()),
        }
    except Exception as e:
        return {"error": f"Failed to read {path}: {e}"}


def write_file(path: str, content: str) -> Dict[str, Any]:
    """Write a file to the repo (governed allowlist only)."""
    if not is_path_allowed(path):
        return {
            "error": f"Path not in allowlist: {path}",
            "allowed_patterns": WRITE_ALLOWLIST_PATTERNS,
        }

    full_path = REPO_ROOT / path

    # Read existing content for governed surface check
    old_content = ""
    if full_path.exists():
        try:
            old_content = full_path.read_text(encoding="utf-8")
        except Exception:
            pass

    # Check for governed surface changes
    warnings = detect_governed_changes(old_content, content)

    # Ensure parent directory exists
    full_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        full_path.write_text(content, encoding="utf-8")
        result = {
            "success": True,
            "path": path,
            "size": len(content),
            "lines": len(content.splitlines()),
        }
        if warnings:
            result["warnings"] = warnings
            result["governed_surface_changes"] = True
        return result
    except Exception as e:
        return {"error": f"Failed to write {path}: {e}"}


def run_ux_tests() -> Dict[str, Any]:
    """Run the Flow Studio UX test suite."""
    results = {
        "success": True,
        "steps": [],
    }

    # Step 1: TypeScript type check
    try:
        ts_check = subprocess.run(
            ["make", "ts-check"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        results["steps"].append(
            {
                "name": "ts-check",
                "success": ts_check.returncode == 0,
                "stdout": ts_check.stdout[-2000:]
                if len(ts_check.stdout) > 2000
                else ts_check.stdout,
                "stderr": ts_check.stderr[-2000:]
                if len(ts_check.stderr) > 2000
                else ts_check.stderr,
            }
        )
        if ts_check.returncode != 0:
            results["success"] = False
    except subprocess.TimeoutExpired:
        results["steps"].append(
            {
                "name": "ts-check",
                "success": False,
                "error": "Timeout (60s)",
            }
        )
        results["success"] = False
    except Exception as e:
        results["steps"].append(
            {
                "name": "ts-check",
                "success": False,
                "error": str(e),
            }
        )
        results["success"] = False

    # Step 2: TypeScript build
    try:
        ts_build = subprocess.run(
            ["make", "ts-build"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        results["steps"].append(
            {
                "name": "ts-build",
                "success": ts_build.returncode == 0,
                "stdout": ts_build.stdout[-2000:]
                if len(ts_build.stdout) > 2000
                else ts_build.stdout,
                "stderr": ts_build.stderr[-2000:]
                if len(ts_build.stderr) > 2000
                else ts_build.stderr,
            }
        )
        if ts_build.returncode != 0:
            results["success"] = False
    except subprocess.TimeoutExpired:
        results["steps"].append(
            {
                "name": "ts-build",
                "success": False,
                "error": "Timeout (60s)",
            }
        )
        results["success"] = False
    except Exception as e:
        results["steps"].append(
            {
                "name": "ts-build",
                "success": False,
                "error": str(e),
            }
        )
        results["success"] = False

    # Step 3: Python UX tests
    test_files = [
        "tests/test_flow_studio_ui_ids.py",
        "tests/test_flow_studio_sdk_path.py",
        "tests/test_flow_studio_a11y.py",
        "tests/test_flow_studio_ux_manifest.py",
    ]
    try:
        pytest_run = subprocess.run(
            ["uv", "run", "pytest"] + test_files + ["-v", "--tb=short"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        results["steps"].append(
            {
                "name": "pytest-ux",
                "success": pytest_run.returncode == 0,
                "stdout": pytest_run.stdout[-4000:]
                if len(pytest_run.stdout) > 4000
                else pytest_run.stdout,
                "stderr": pytest_run.stderr[-2000:]
                if len(pytest_run.stderr) > 2000
                else pytest_run.stderr,
            }
        )
        if pytest_run.returncode != 0:
            results["success"] = False
    except subprocess.TimeoutExpired:
        results["steps"].append(
            {
                "name": "pytest-ux",
                "success": False,
                "error": "Timeout (120s)",
            }
        )
        results["success"] = False
    except Exception as e:
        results["steps"].append(
            {
                "name": "pytest-ux",
                "success": False,
                "error": str(e),
            }
        )
        results["success"] = False

    return results


def list_ui_files() -> Dict[str, Any]:
    """List all files in the Flow Studio UI source directories."""
    files = {
        "typescript": [],
        "css": [],
        "docs": [],
    }

    # TypeScript files
    ts_dir = REPO_ROOT / "swarm" / "tools" / "flow_studio_ui" / "src"
    if ts_dir.exists():
        for f in sorted(ts_dir.glob("**/*.ts")):
            files["typescript"].append(str(f.relative_to(REPO_ROOT)))

    # CSS files
    css_dir = REPO_ROOT / "swarm" / "tools" / "flow_studio_ui" / "css"
    if css_dir.exists():
        for f in sorted(css_dir.glob("**/*.css")):
            files["css"].append(str(f.relative_to(REPO_ROOT)))

    # Doc files
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.exists():
        for f in sorted(docs_dir.glob("FLOW_STUDIO*.md")):
            files["docs"].append(str(f.relative_to(REPO_ROOT)))

    return files


# ============================================================================
# MCP Server
# ============================================================================


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("ux_repo")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="read_file",
                description=(
                    "Read a UTF-8 text file from the repo. "
                    "Any file in the repo can be read for context."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path relative to repo root (e.g., 'swarm/tools/flow_studio_ui/src/domain.ts')",
                        },
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="write_file",
                description=(
                    "Write a UTF-8 text file to the repo. "
                    "Only files matching the governed allowlist can be written. "
                    "Warns if changes touch governed surfaces (SDK fields, UIIDs, data-ui-ready)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path relative to repo root (must match allowlist)",
                        },
                        "content": {
                            "type": "string",
                            "description": "File content to write",
                        },
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="run_ux_tests",
                description=(
                    "Run the Flow Studio UX test suite: ts-check, ts-build, and pytest. "
                    "Returns success status and output for each step."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="list_ui_files",
                description=(
                    "List all files in the Flow Studio UI directories. "
                    "Returns TypeScript, CSS, and doc files that can be modified."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_write_allowlist",
                description=(
                    "Get the list of file patterns that can be written. "
                    "Useful for understanding what files the implementer can modify."
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
        if name == "read_file":
            result = read_file(arguments["path"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "write_file":
            result = write_file(arguments["path"], arguments["content"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "run_ux_tests":
            result = run_ux_tests()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "list_ui_files":
            result = list_ui_files()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_write_allowlist":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "patterns": WRITE_ALLOWLIST_PATTERNS,
                            "governed_surfaces": GOVERNED_SURFACE_PATTERNS,
                        },
                        indent=2,
                    ),
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
