"""Hook protocols and factory functions for the Claude SDK integration.

This module provides:
- PreToolUseHook and PostToolUseHook protocols
- Factory functions for common guardrail hooks
- Factory functions for telemetry hooks

These are SDK-free modules (no SDK calls involved).
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Hook Protocols for Guardrails and Telemetry
# =============================================================================


class PreToolUseHook(Protocol):
    """Protocol for hooks called before tool execution.

    PreToolUse hooks can:
    - Inspect the tool call before execution
    - Block the tool call by returning (False, reason)
    - Allow the tool call by returning (True, None)
    - Modify context (via side effects) for telemetry

    Example:
        >>> def my_pre_hook(tool_name, tool_input, context):
        ...     if tool_name == "Bash" and "rm -rf" in tool_input.get("command", ""):
        ...         return (False, "Dangerous command blocked")
        ...     context["tool_start_time"] = time.time()
        ...     return (True, None)
    """

    def __call__(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Called before tool execution.

        Args:
            tool_name: Name of the tool being called (e.g., "Bash", "Edit").
            tool_input: Input parameters for the tool.
            context: Mutable context dict for passing data to post-hook.

        Returns:
            Tuple of (allow, reason). If allow is False, tool is blocked with reason.
        """
        ...


class PostToolUseHook(Protocol):
    """Protocol for hooks called after tool execution.

    PostToolUse hooks can:
    - Inspect the tool result
    - Record metrics/telemetry
    - Log or audit tool usage

    Example:
        >>> def my_post_hook(tool_name, tool_input, result, context):
        ...     elapsed = time.time() - context.get("tool_start_time", 0)
        ...     logger.info(f"Tool {tool_name} completed in {elapsed:.2f}s")
    """

    def __call__(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        result: Any,
        success: bool,
        context: Dict[str, Any],
    ) -> None:
        """Called after tool execution.

        Args:
            tool_name: Name of the tool that was called.
            tool_input: Input parameters that were passed.
            result: The tool result (may be truncated).
            success: Whether the tool execution succeeded.
            context: Context dict shared with pre-hook.
        """
        ...


# =============================================================================
# Hook Factory Functions for Common Guardrails and Telemetry
# =============================================================================


def create_dangerous_command_hook(
    blocked_patterns: Optional[List[str]] = None,
) -> PreToolUseHook:
    """Create a pre-tool-use hook that blocks dangerous shell commands.

    This hook inspects Bash tool calls and blocks commands matching dangerous patterns.
    Used for safety guardrails in agentic execution.

    Args:
        blocked_patterns: List of regex patterns to block. Defaults to common dangerous
            commands like 'rm -rf', 'git push --force', etc.

    Returns:
        A PreToolUseHook that blocks dangerous commands.

    Example:
        >>> hook = create_dangerous_command_hook()
        >>> client = StepSessionClient(pre_tool_hooks=[hook])
    """
    if blocked_patterns is None:
        blocked_patterns = [
            r"rm\s+-rf\s+/",  # rm -rf / (root deletion)
            r"rm\s+-rf\s+\*",  # rm -rf * (wildcard deletion)
            r"git\s+push\s+.*--force",  # Force push
            r"git\s+reset\s+--hard",  # Hard reset
            r"chmod\s+-R\s+777",  # Overly permissive chmod
            r"sudo\s+rm",  # sudo rm commands
            r":(){ :|:& };:",  # Fork bomb
            r"mkfs\.",  # Filesystem formatting
            r"dd\s+if=/dev/zero",  # Disk overwrite
        ]

    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in blocked_patterns]

    def hook(
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        if tool_name != "Bash":
            return (True, None)

        command = tool_input.get("command", "")
        for pattern in compiled_patterns:
            if pattern.search(command):
                return (False, f"Dangerous command pattern blocked: {pattern.pattern}")

        return (True, None)

    return hook


def create_telemetry_hook() -> Tuple[PreToolUseHook, PostToolUseHook]:
    """Create pre/post hook pair for collecting tool execution telemetry.

    Returns:
        Tuple of (pre_hook, post_hook) for tool timing telemetry.

    Example:
        >>> pre_hook, post_hook = create_telemetry_hook()
        >>> client = StepSessionClient(
        ...     pre_tool_hooks=[pre_hook],
        ...     post_tool_hooks=[post_hook],
        ... )
    """

    def pre_hook(
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        context["tool_start_time"] = time.time()
        context["tool_input"] = tool_input
        return (True, None)

    def post_hook(
        tool_name: str,
        tool_input: Dict[str, Any],
        result: Any,
        success: bool,
        context: Dict[str, Any],
    ) -> None:
        start_time = context.get("tool_start_time", 0)
        duration_ms = (time.time() - start_time) * 1000 if start_time else 0
        logger.debug(
            "Tool %s completed in %.2f ms (success=%s)",
            tool_name,
            duration_ms,
            success,
        )

    return pre_hook, post_hook


def create_file_access_audit_hook(
    audit_log: Optional[List[Dict[str, Any]]] = None,
) -> PostToolUseHook:
    """Create a post-tool-use hook that audits file access.

    Records all Read, Write, and Edit tool calls to an audit log.

    Args:
        audit_log: Optional list to append audit entries to. If None, logs to logger.

    Returns:
        A PostToolUseHook for file access auditing.

    Example:
        >>> audit_log = []
        >>> hook = create_file_access_audit_hook(audit_log)
        >>> client = StepSessionClient(post_tool_hooks=[hook])
        >>> # After execution:
        >>> for entry in audit_log:
        ...     print(f"{entry['tool']}: {entry['path']}")
    """

    def hook(
        tool_name: str,
        tool_input: Dict[str, Any],
        result: Any,
        success: bool,
        context: Dict[str, Any],
    ) -> None:
        if tool_name not in ("Read", "Write", "Edit"):
            return

        file_path = tool_input.get("file_path", tool_input.get("path", ""))
        entry = {
            "tool": tool_name,
            "path": file_path,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "session_id": context.get("session_id", ""),
            "step_id": context.get("step_id", ""),
        }

        if audit_log is not None:
            audit_log.append(entry)
        else:
            logger.info(
                "File access audit: %s %s (success=%s)",
                tool_name,
                file_path,
                success,
            )

    return hook


def create_token_budget_hook(
    max_prompt_tokens: int = 100000,
    max_completion_tokens: int = 50000,
    on_budget_exceeded: Optional[Callable[[str, int, int], None]] = None,
) -> PostToolUseHook:
    """Create a hook that tracks token budget consumption.

    Note: This hook tracks tokens at the tool result level. For full budget tracking,
    also monitor the ResultEvent token counts in each phase.

    Args:
        max_prompt_tokens: Maximum prompt tokens allowed.
        max_completion_tokens: Maximum completion tokens allowed.
        on_budget_exceeded: Optional callback when budget is exceeded.
            Called with (budget_type, current_value, max_value).

    Returns:
        A PostToolUseHook for token budget tracking.
    """
    token_counts = {"prompt": 0, "completion": 0}

    def hook(
        tool_name: str,
        tool_input: Dict[str, Any],
        result: Any,
        success: bool,
        context: Dict[str, Any],
    ) -> None:
        # Estimate tokens from tool result if available
        # This is a rough estimate; actual tokens come from ResultEvent
        if isinstance(result, str):
            estimated_tokens = len(result) // 4  # Rough char-to-token ratio
            token_counts["completion"] += estimated_tokens

            if token_counts["completion"] > max_completion_tokens:
                if on_budget_exceeded:
                    on_budget_exceeded(
                        "completion",
                        token_counts["completion"],
                        max_completion_tokens,
                    )
                else:
                    logger.warning(
                        "Token budget exceeded: completion=%d > max=%d",
                        token_counts["completion"],
                        max_completion_tokens,
                    )

    return hook
