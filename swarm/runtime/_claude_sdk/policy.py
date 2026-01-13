"""Tool policy and command blocking for the Claude SDK integration.

This module provides:
- Command pattern matching for blocking dangerous commands
- Tool policy hooks for high-trust execution
- Tool restriction helpers for deterministic behavior

These are SDK-free modules (no SDK calls involved).
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from swarm.runtime._claude_sdk.constants import (
    ALL_STANDARD_TOOLS,
    BLOCKED_COMMAND_PATTERNS,
)

# Compiled patterns for efficiency
_BLOCKED_PATTERNS_COMPILED: List[re.Pattern[str]] = []


def _get_blocked_patterns() -> List[re.Pattern[str]]:
    """Get compiled blocked command patterns (lazy initialization)."""
    global _BLOCKED_PATTERNS_COMPILED
    if not _BLOCKED_PATTERNS_COMPILED:
        _BLOCKED_PATTERNS_COMPILED = [
            re.compile(pattern, re.IGNORECASE) for pattern in BLOCKED_COMMAND_PATTERNS
        ]
    return _BLOCKED_PATTERNS_COMPILED


def is_blocked_command(command: str) -> Tuple[bool, Optional[str]]:
    """Check if a command matches any blocked pattern.

    Args:
        command: The command string to check.

    Returns:
        Tuple of (is_blocked, matched_pattern) where matched_pattern is the
        pattern that matched if blocked, None otherwise.
    """
    for pattern in _get_blocked_patterns():
        if pattern.search(command):
            return True, pattern.pattern
    return False, None


def create_tool_policy_hook(
    allow_write: bool = True,
    allow_bash: bool = True,
    blocked_paths: Optional[List[str]] = None,
) -> Callable[[str, Dict[str, Any]], Tuple[bool, Optional[str]]]:
    """Create a tool policy hook for can_use_tool validation.

    This implements the high-trust tool policy:
    - Broad access by default (don't revert to tiny allowlists)
    - Block obvious foot-guns via pattern matching
    - Optionally restrict certain paths

    Args:
        allow_write: Whether to allow Write/Edit tools.
        allow_bash: Whether to allow Bash tool.
        blocked_paths: Optional list of path prefixes to block.

    Returns:
        A callable that takes (tool_name, tool_input) and returns
        (allow, reason) where allow is True if the tool use is permitted.

    Example:
        >>> hook = create_tool_policy_hook(blocked_paths=["/etc", "/usr"])
        >>> hook("Bash", {"command": "rm -rf /"})
        (False, 'Command matches blocked pattern: rm\\s+-rf\\s+/')
    """
    blocked_path_list = blocked_paths or []

    def tool_policy_hook(tool_name: str, tool_input: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Tool policy hook for can_use_tool validation."""
        # Check tool-level permissions
        if tool_name in ("Write", "Edit") and not allow_write:
            return False, "Write operations not permitted in this context"

        if tool_name == "Bash" and not allow_bash:
            return False, "Bash commands not permitted in this context"

        # Check blocked command patterns for Bash
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            is_blocked, pattern = is_blocked_command(command)
            if is_blocked:
                return False, f"Command matches blocked pattern: {pattern}"

        # Check blocked paths for file operations
        if tool_name in ("Read", "Write", "Edit", "Glob", "Grep"):
            file_path = tool_input.get("file_path") or tool_input.get("path", "")
            for blocked in blocked_path_list:
                if file_path.startswith(blocked):
                    return False, f"Path {file_path} is in blocked path: {blocked}"

        # Default: allow
        return True, None

    return tool_policy_hook


def compute_disallowed_tools(allowed_tools: Optional[List[str]]) -> Optional[List[str]]:
    """Compute disallowed_tools for deterministic tool restriction.

    The Claude SDK requires BOTH allowed_tools AND disallowed_tools to be set
    for deterministic tool restriction. allowed_tools alone may only affect
    permission prompting, not actual enforcement.

    This function computes the complement of allowed_tools from the set of
    all standard Claude Code tools, enabling proper tool restriction.

    Args:
        allowed_tools: List of tools to allow, or None for all tools.

    Returns:
        List of tools to explicitly disallow, or None if all tools allowed.

    Example:
        >>> allowed = ["Read", "Glob", "Grep"]
        >>> disallowed = compute_disallowed_tools(allowed)
        >>> # disallowed contains Write, Edit, Bash, etc.
    """
    if allowed_tools is None:
        return None  # No restriction - all tools allowed

    allowed_set = frozenset(allowed_tools)
    disallowed = [t for t in ALL_STANDARD_TOOLS if t not in allowed_set]
    return disallowed if disallowed else None
