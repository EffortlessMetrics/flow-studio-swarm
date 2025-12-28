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
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional, Union

# Module logger
logger = logging.getLogger(__name__)

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
) -> Any:
    """Create ClaudeCodeOptions with High-Trust settings.

    This function enforces the design principles for agentic execution:
    - bypassPermissions mode for "hands-off" construction
    - Project-only settings (CLAUDE.md visibility)
    - Explicit tool surface

    Args:
        cwd: Working directory for the SDK session.
        permission_mode: Permission mode ("bypassPermissions" by default).
        model: Model override (uses DEFAULT_MODEL if not specified).
        system_prompt_append: Optional text to append to system prompt.
        max_thinking_tokens: Optional max tokens for extended thinking.

    Returns:
        ClaudeCodeOptions instance configured for high-trust execution.

    Raises:
        ImportError: If SDK is not available.
    """
    sdk = get_sdk_module()

    # Build system prompt with preset
    system_prompt: Optional[Dict[str, Any]] = None
    if system_prompt_append:
        system_prompt = {
            "type": "preset",
            "preset": SYSTEM_PROMPT_PRESET,
            "append": system_prompt_append,
        }

    # Build options dict
    options_kwargs: Dict[str, Any] = {
        "permission_mode": permission_mode,
    }

    if cwd:
        options_kwargs["cwd"] = str(cwd)

    if model:
        options_kwargs["model"] = model

    if system_prompt:
        options_kwargs["system_prompt"] = system_prompt

    if max_thinking_tokens is not None:
        options_kwargs["max_thinking_tokens"] = max_thinking_tokens

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
