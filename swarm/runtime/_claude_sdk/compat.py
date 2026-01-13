"""Compatibility shims for the Claude SDK adapter.

This module provides backward compatibility helpers for gradual migration
from older formats to newer standardized types.
"""

from typing import Any, Dict

from swarm.runtime.types.tool_call import NormalizedToolCall


def _dict_to_normalized_tool_call(d: Dict[str, Any]) -> NormalizedToolCall:
    """Convert legacy dict format to NormalizedToolCall.

    This helper enables gradual migration from the old dict-based tool call
    tracking to the new NormalizedToolCall format. Use it when consuming
    tool calls from older code paths or external sources.

    Args:
        d: Dictionary with legacy tool call fields. Supports both old keys
           ("tool", "input", "output") and new keys ("tool_name", "tool_input",
           "tool_output").

    Returns:
        NormalizedToolCall instance with fields mapped from the dictionary.

    Example:
        >>> old_tool_call = {
        ...     "tool": "Bash",
        ...     "input": {"command": "ls -la"},
        ...     "output": "total 42...",
        ...     "timestamp": "2024-01-01T00:00:00Z",
        ... }
        >>> normalized = _dict_to_normalized_tool_call(old_tool_call)
        >>> normalized.tool_name
        'Bash'
    """
    return NormalizedToolCall(
        tool_name=d.get("tool", d.get("tool_name", "unknown")),
        tool_input=d.get("input", d.get("tool_input", {})),
        tool_output=d.get("output", d.get("tool_output")),
        success=d.get("success", True),
        duration_ms=d.get("duration_ms", 0),
        blocked=d.get("blocked", False),
        blocked_reason=d.get("blocked_reason"),
        source=d.get("source", "sdk"),
        timestamp=d.get("timestamp"),
    )
