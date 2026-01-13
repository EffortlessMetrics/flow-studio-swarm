"""Configuration constants for the Claude SDK integration.

This module contains global configuration constants used throughout the
Claude SDK integration, including:

- Sandbox configuration (prepared for future SDK support)
- Default model and system prompt settings
- Blocked command patterns for safety
- Standard tool definitions for tool restriction
"""

import os
from typing import List

# =============================================================================
# Sandbox Configuration (NOT IMPLEMENTED)
# =============================================================================
# IMPORTANT: Sandbox enforcement is NOT currently implemented in the SDK.
# These settings are preserved for future SDK support, but currently only
# affect logging output. Commands have full host access regardless of settings.
#
# When the SDK adds sandbox support, we can enable actual enforcement.
# Until then, treat all execution as unsandboxed.

# Intentionally defaults to False to avoid false sense of safety
SANDBOX_ENABLED = os.environ.get("SWARM_SANDBOX_ENABLED", "false").lower() == "true"
ALLOW_UNSANDBOXED = os.environ.get("SWARM_ALLOW_UNSANDBOXED", "true").lower() == "true"

# Preserved for future SDK support
DEFAULT_SANDBOX_ALLOWED_COMMANDS = [
    "git",
    "npm",
    "npx",
    "pnpm",
    "uv",
    "pip",
    "pytest",
    "cargo",
    "rustc",
    "make",
    "python",
    "node",
]

# Warning flag to log sandbox status on first use
_SANDBOX_WARNING_LOGGED = False


# =============================================================================
# Default Model and System Prompt Settings
# =============================================================================

# Default model for step execution
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# System prompt preset for Claude Code behavior
SYSTEM_PROMPT_PRESET = "claude_code"


# =============================================================================
# High-Trust Tool Policy
# =============================================================================

# Blocked commands/patterns that are obvious foot-guns
# These are patterns that should NEVER be executed in agentic mode
BLOCKED_COMMAND_PATTERNS: List[str] = [
    # Destructive git operations
    r"git\s+push\s+.*--force",
    r"git\s+push\s+-f\b",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-fd",
    r"git\s+checkout\s+--\s+\.",  # Discard all changes
    r"git\s+branch\s+-D",  # Force delete branch
    # Destructive file operations
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\$HOME",
    r"del\s+/s\s+/q\s+[cC]:\\",  # Windows recursive delete
    r"rmdir\s+/s\s+/q\s+[cC]:\\",
    # Dangerous system commands
    r":(){ :|:& };:",  # Fork bomb
    r"chmod\s+-R\s+777\s+/",
    r"chown\s+-R\s+.*\s+/",
    # Environment destruction
    r"unset\s+PATH",
    r"export\s+PATH\s*=\s*$",
]


# =============================================================================
# Tool Restriction Helpers for Deterministic Behavior
# =============================================================================

# Standard Claude Code tools that can be explicitly blocked.
# IMPORTANT: For deterministic tool restriction, the SDK requires BOTH
# allowed_tools AND disallowed_tools to be set. allowed_tools alone may only
# affect permission prompting, not actual enforcement.
# See: platform.claude.com/cookbook/claude-agent-sdk-02
ALL_STANDARD_TOOLS = frozenset([
    "Read", "Write", "Edit", "MultiEdit",
    "Bash", "Glob", "Grep",
    "BashOutput", "KillBash",
    "WebFetch", "WebSearch",
    "TodoRead", "TodoWrite",
    "Task", "Agent",
    "NotebookEdit", "NotebookRead",
    "AskUserQuestion",
    "ExitPlanMode",
    "ListMcpResources", "ReadMcpResource",
])
