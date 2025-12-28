"""
claude_sdk.py - Unified Claude SDK adapter with deterministic options.

This module is the ONLY place that imports the Claude Code SDK package(s).
It provides:
1. Clean imports with fallback handling
2. A single "options builder" that enforces High-Trust design
3. Helper functions for common SDK operations

Usage:
    from swarm.runtime.claude_sdk import (
        SDK_AVAILABLE,
        create_high_trust_options,
        create_options_from_plan,
        query_with_options,
        get_sdk_module,
    )

Design Principles:
    - Single import point for SDK
    - Options always set: cwd, permission_mode, system_prompt preset
    - Explicit tool surface policy
    - Project-only settings by default
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Optional, Union

if TYPE_CHECKING:
    from swarm.spec.types import PromptPlan

# Module logger
logger = logging.getLogger(__name__)

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
    "git", "npm", "npx", "pnpm", "uv", "pip", "pytest",
    "cargo", "rustc", "make", "python", "node",
]

# Warning flag to log sandbox status on first use
_SANDBOX_WARNING_LOGGED = False

# =============================================================================
# SDK Availability Detection
# =============================================================================

SDK_AVAILABLE: bool = False
_sdk_module: Optional[Any] = None
_sdk_import_error: Optional[str] = None

try:
    import claude_code_sdk
    _sdk_module = claude_code_sdk
    SDK_AVAILABLE = True
    logger.debug("claude_code_sdk imported successfully")
except ImportError as e:
    _sdk_import_error = str(e)
    logger.debug("claude_code_sdk not available: %s", e)


def get_sdk_module() -> Any:
    """Get the Claude Code SDK module.

    Returns:
        The claude_code_sdk module.

    Raises:
        ImportError: If SDK is not available.
    """
    if not SDK_AVAILABLE:
        raise ImportError(
            f"Claude Code SDK is not available: {_sdk_import_error}. "
            "Install with: pip install claude-code-sdk"
        )
    return _sdk_module


def check_sdk_available() -> bool:
    """Check if the Claude Code SDK is available.

    Returns:
        True if SDK can be imported, False otherwise.
    """
    return SDK_AVAILABLE


# =============================================================================
# Options Builder
# =============================================================================

# Default model for step execution
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# System prompt preset for Claude Code behavior
SYSTEM_PROMPT_PRESET = "claude_code"


def create_high_trust_options(
    cwd: Optional[Union[str, Path]] = None,
    permission_mode: str = "bypassPermissions",
    model: Optional[str] = None,
    system_prompt_append: Optional[str] = None,
    max_thinking_tokens: Optional[int] = None,
    max_turns: Optional[int] = None,
    sandboxed: Optional[bool] = None,
) -> Any:
    """Create ClaudeCodeOptions with High-Trust settings.

    This function enforces the design principles for agentic execution:
    - bypassPermissions mode for "hands-off" construction
    - Project-only settings (CLAUDE.md visibility)
    - System prompt preset for consistent Claude Code behavior
    - Explicit tool surface
    - Sandbox control for command containment

    MANDATORY SETTINGS (always enforced):
    - setting_sources=["project"]: Loads CLAUDE.md and .claude/skills
    - permission_mode: Controls file/command permissions
    - system_prompt preset: "claude_code" for consistent behavior

    SANDBOX BEHAVIOR:
    - If sandboxed is None, uses SWARM_SANDBOX_ENABLED env var (default True)
    - If sandboxed is False, requires SWARM_ALLOW_UNSANDBOXED=true
    - Sandbox limits command execution to a safe subset

    Args:
        cwd: Working directory for the SDK session (REQUIRED for reliable execution).
        permission_mode: Permission mode ("bypassPermissions" by default).
        model: Model override (uses DEFAULT_MODEL if not specified).
        system_prompt_append: Optional text to append to system prompt (persona, context).
        max_thinking_tokens: Optional max tokens for extended thinking.
        max_turns: Optional max conversation turns within this query (default: unlimited).
        sandboxed: Enable sandbox containment. None uses SWARM_SANDBOX_ENABLED env var.

    Returns:
        ClaudeCodeOptions instance configured for high-trust execution.

    Raises:
        ImportError: If SDK is not available.
    """
    sdk = get_sdk_module()

    # ALWAYS use system prompt preset for consistent Claude Code behavior
    # This ensures the agent behaves like Claude Code (tools, file ops, etc.)
    system_prompt: Dict[str, Any] = {
        "type": "preset",
        "preset": SYSTEM_PROMPT_PRESET,
    }
    if system_prompt_append:
        system_prompt["append"] = system_prompt_append

    # Build options dict with MANDATORY settings
    # CRITICAL: These settings are required for reliable agentic execution
    options_kwargs: Dict[str, Any] = {
        # 1. Permission mode: "bypassPermissions" for autonomous execution
        "permission_mode": permission_mode,
        # 2. Setting sources: ["project"] ensures CLAUDE.md and skills are loaded
        "setting_sources": ["project"],
        # 3. System prompt: preset for Claude Code behavior
        "system_prompt": system_prompt,
    }

    # Working directory (strongly recommended)
    if cwd:
        options_kwargs["cwd"] = str(cwd)
    else:
        logger.warning(
            "create_high_trust_options called without cwd - "
            "execution may fail or use unexpected working directory"
        )

    # Optional overrides
    if model:
        options_kwargs["model"] = model

    if max_thinking_tokens is not None:
        options_kwargs["max_thinking_tokens"] = max_thinking_tokens

    if max_turns is not None:
        options_kwargs["max_turns"] = max_turns

    # Handle sandbox configuration
    # NOTE: Sandbox enforcement is NOT currently implemented in the SDK.
    # This code path exists for future SDK support only.
    global _SANDBOX_WARNING_LOGGED

    if sandboxed is None:
        sandboxed = SANDBOX_ENABLED

    # Log honest sandbox status (once per process)
    if not _SANDBOX_WARNING_LOGGED:
        logger.info(
            "Sandbox status: NOT IMPLEMENTED. Commands have full host access. "
            "SWARM_SANDBOX_ENABLED=%s has no effect until SDK adds support.",
            SANDBOX_ENABLED,
        )
        _SANDBOX_WARNING_LOGGED = True

    # Preserved for future SDK support - currently no-op
    # When SDK adds sandboxSettings, uncomment this:
    # options_kwargs["sandboxSettings"] = {
    #     "enabled": sandboxed,
    #     "allowedCommands": DEFAULT_SANDBOX_ALLOWED_COMMANDS,
    # }

    return sdk.ClaudeCodeOptions(**options_kwargs)


def create_options_from_plan(
    plan: "PromptPlan",
    cwd: Optional[Union[str, Path]] = None,
) -> Any:
    """Create ClaudeCodeOptions from a compiled PromptPlan.

    This function maps spec-defined settings from a PromptPlan to SDK options,
    enabling the spec-first architecture where execution parameters are derived
    from machine-readable contracts rather than filesystem configuration.

    The PromptPlan contains all SDK configuration needed for execution:
    - model: The model to use (e.g., "sonnet", "opus")
    - permission_mode: Permission mode for the SDK session
    - allowed_tools: Tools available to the agent (informational in high-trust mode)
    - max_turns: Maximum conversation turns
    - sandbox_enabled: Sandbox configuration (prepared for future SDK support)
    - system_append: Text to append to the system prompt

    Args:
        plan: A compiled PromptPlan containing SDK configuration.
        cwd: Optional working directory override. If not specified, uses plan.cwd.

    Returns:
        ClaudeCodeOptions instance configured from the PromptPlan.

    Raises:
        RuntimeError: If the Claude SDK is not available.

    Example:
        >>> from swarm.spec.types import PromptPlan
        >>> plan = compile_prompt_plan(station, flow, step, ctx)
        >>> options = create_options_from_plan(plan)
        >>> async for event in sdk.query(prompt=plan.user_prompt, options=options):
        ...     process(event)
    """
    if not SDK_AVAILABLE:
        raise RuntimeError(
            f"Claude SDK not available: {_sdk_import_error}. "
            "Install with: pip install claude-code-sdk"
        )
    sdk = _sdk_module

    # Determine effective cwd - prefer explicit parameter, then plan.cwd
    effective_cwd: Optional[str] = None
    if cwd is not None:
        effective_cwd = str(cwd)
    elif plan.cwd:
        effective_cwd = plan.cwd

    # Build system prompt with preset and optional append
    system_prompt: Dict[str, Any] = {
        "type": "preset",
        "preset": SYSTEM_PROMPT_PRESET,
    }
    if plan.system_append:
        system_prompt["append"] = plan.system_append

    # Map permission mode from plan (with fallback)
    permission_mode = plan.permission_mode or "bypassPermissions"

    # Build options with MANDATORY settings from spec
    options_kwargs: Dict[str, Any] = {
        # 1. Permission mode from plan (or default)
        "permission_mode": permission_mode,
        # 2. Setting sources: ["project"] ensures CLAUDE.md and skills are loaded
        "setting_sources": ["project"],
        # 3. System prompt: preset + append from plan
        "system_prompt": system_prompt,
    }

    # Working directory
    if effective_cwd:
        options_kwargs["cwd"] = effective_cwd
    else:
        logger.warning(
            "create_options_from_plan called without cwd and plan.cwd is empty - "
            "execution may fail or use unexpected working directory"
        )

    # Model from plan (map short names to full model IDs if needed)
    if plan.model:
        # The plan.model may be a short name like "sonnet" or full ID
        # For now, pass through - the SDK handles model resolution
        options_kwargs["model"] = plan.model

    # Max turns from plan
    if plan.max_turns:
        options_kwargs["max_turns"] = plan.max_turns

    # NOTE: allowed_tools is informational in high-trust mode.
    # The agent has full toolbox access via bypassPermissions.
    # allowed_tools is preserved in the PromptPlan for:
    # 1. Documentation of intended tool surface
    # 2. Future SDK support for tool restrictions
    # 3. Audit/compliance logging
    #
    # For now, we log the intended tools but don't restrict.
    if plan.allowed_tools:
        logger.debug(
            "PromptPlan specifies allowed_tools=%s (informational only in high-trust mode)",
            plan.allowed_tools,
        )

    # NOTE: sandbox_enabled is prepared for future SDK support.
    # Currently no-op, same as create_high_trust_options().
    if plan.sandbox_enabled:
        logger.debug(
            "PromptPlan specifies sandbox_enabled=True (not enforced until SDK adds support)"
        )

    return sdk.ClaudeCodeOptions(**options_kwargs)


# =============================================================================
# Query Helpers
# =============================================================================


async def query_with_options(
    prompt: str,
    options: Any,
) -> AsyncIterator[Any]:
    """Execute a query with the provided options.

    This is a thin wrapper around sdk.query() that provides:
    - Consistent error handling
    - Logging
    - Type hints

    Args:
        prompt: The prompt to send to the SDK.
        options: ClaudeCodeOptions instance.

    Yields:
        SDK events from the query response.

    Raises:
        ImportError: If SDK is not available.
    """
    sdk = get_sdk_module()

    async for event in sdk.query(prompt=prompt, options=options):
        yield event


async def query_simple(
    prompt: str,
    cwd: Optional[Union[str, Path]] = None,
    permission_mode: str = "bypassPermissions",
) -> AsyncIterator[Any]:
    """Execute a simple query with default high-trust options.

    Convenience function for common use cases.

    Args:
        prompt: The prompt to send.
        cwd: Optional working directory.
        permission_mode: Permission mode (default: bypassPermissions).

    Yields:
        SDK events from the query response.
    """
    options = create_high_trust_options(
        cwd=cwd,
        permission_mode=permission_mode,
    )

    async for event in query_with_options(prompt, options):
        yield event


# =============================================================================
# Event Processing Helpers
# =============================================================================


def extract_text_from_event(event: Any) -> Optional[str]:
    """Extract text content from an SDK event.

    Handles different event types and content structures.

    Args:
        event: An SDK event object.

    Returns:
        Extracted text or None if no text content.
    """
    if not event:
        return None

    # Check for direct message attribute
    if hasattr(event, "message"):
        return str(event.message)

    # Check for content blocks
    if hasattr(event, "content"):
        content = event.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for block in content:
                if hasattr(block, "text"):
                    texts.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
            if texts:
                return "\n".join(texts)

    return None


def is_result_message(event: Any) -> bool:
    """Check if an event is a ResultMessage.

    Args:
        event: An SDK event object.

    Returns:
        True if event is a ResultMessage.
    """
    return type(event).__name__ == "ResultMessage"


def is_assistant_message(event: Any) -> bool:
    """Check if an event is an AssistantMessage.

    Args:
        event: An SDK event object.

    Returns:
        True if event is an AssistantMessage.
    """
    return type(event).__name__ == "AssistantMessage"


def is_tool_use(event: Any) -> bool:
    """Check if an event contains tool use.

    Args:
        event: An SDK event object.

    Returns:
        True if event contains tool use content.
    """
    if not hasattr(event, "content"):
        return False

    content = event.content
    if not isinstance(content, list):
        return False

    for block in content:
        if hasattr(block, "type") and block.type == "tool_use":
            return True
        if isinstance(block, dict) and block.get("type") == "tool_use":
            return True

    return False


def extract_usage_from_event(event: Any) -> Dict[str, int]:
    """Extract token usage from a ResultMessage event.

    Args:
        event: A ResultMessage event.

    Returns:
        Dict with prompt/completion/total token counts.
    """
    usage = {"prompt": 0, "completion": 0, "total": 0}

    if not hasattr(event, "total_cost_usd"):
        # Not a ResultMessage, try other attributes
        if hasattr(event, "usage"):
            raw = event.usage
            if hasattr(raw, "input_tokens"):
                usage["prompt"] = raw.input_tokens
            if hasattr(raw, "output_tokens"):
                usage["completion"] = raw.output_tokens
            usage["total"] = usage["prompt"] + usage["completion"]
        return usage

    # ResultMessage structure
    if hasattr(event, "total_input_tokens"):
        usage["prompt"] = event.total_input_tokens
    if hasattr(event, "total_output_tokens"):
        usage["completion"] = event.total_output_tokens
    usage["total"] = usage["prompt"] + usage["completion"]

    return usage


def extract_model_from_event(event: Any) -> Optional[str]:
    """Extract model name from an event.

    Args:
        event: An SDK event object.

    Returns:
        Model name string or None.
    """
    if hasattr(event, "model"):
        return event.model
    return None
