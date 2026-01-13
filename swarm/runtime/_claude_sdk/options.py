"""Options builder for the Claude SDK integration.

This module provides functions for creating ClaudeCodeOptions with High-Trust
settings, enforcing the design principles for agentic execution.

Usage:
    from swarm.runtime._claude_sdk.options import (
        create_high_trust_options,
        create_options_from_plan,
    )
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from typing_extensions import TYPE_CHECKING

from swarm.runtime._claude_sdk.constants import (
    DEFAULT_MODEL,
    SANDBOX_ENABLED,
    SYSTEM_PROMPT_PRESET,
    _SANDBOX_WARNING_LOGGED,
)
from swarm.runtime._claude_sdk.policy import compute_disallowed_tools
from swarm.runtime._claude_sdk.sdk_import import get_sdk_module

if TYPE_CHECKING:
    from swarm.spec.types import PromptPlan

# Module logger
logger = logging.getLogger(__name__)


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

    TOOL RESTRICTION SEMANTICS:
    For deterministic tool restriction, the SDK requires BOTH allowed_tools AND
    disallowed_tools to be set. allowed_tools alone may only affect permission
    prompting, not actual enforcement. Use compute_disallowed_tools() to derive
    the disallowed_tools list from an allowed_tools list.
    See: platform.claude.com/cookbook/claude-agent-sdk-02

    SANDBOX BEHAVIOR:
    - If sandboxed is None, uses SWARM_SANDBOX_ENABLED env var (default True)
    - If sandboxed is False, requires SWARM_ALLOW_UNSANDBOXED=true
    - Sandbox limits command execution to a safe subset

    CHECKPOINTING (NOT ENABLED):
    The SDK supports file checkpointing via enable_file_checkpointing=True,
    but Flow Studio does not use this. Resumability is handled via disk-based
    receipts and artifacts at step boundaries. This aligns with the session
    amnesia model where each step starts fresh and rehydrates from disk.
    See: TransportCapabilities.supports_rewind docs in transports/port.py
    See: docs/reference/SDK_CAPABILITIES.md for full capability matrix.

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

    # The SDK now exports ClaudeAgentOptions instead of ClaudeCodeOptions
    return sdk.ClaudeAgentOptions(**options_kwargs)


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
    from swarm.runtime._claude_sdk.sdk_import import SDK_AVAILABLE, _sdk_import_error

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

    # IMPORTANT: For deterministic tool restriction, both allowed_tools AND
    # disallowed_tools must be set. allowed_tools alone may only affect
    # permission prompting. See: platform.claude.com/cookbook/claude-agent-sdk-02
    #
    # When allowed_tools is specified in the PromptPlan, we compute the
    # disallowed_tools to ensure deterministic behavior.
    if plan.allowed_tools:
        options_kwargs["allowed_tools"] = plan.allowed_tools
        disallowed = compute_disallowed_tools(plan.allowed_tools)
        if disallowed:
            options_kwargs["disallowed_tools"] = disallowed
        logger.debug(
            "PromptPlan specifies allowed_tools=%s, computed disallowed_tools=%s",
            plan.allowed_tools,
            disallowed,
        )

    # NOTE: sandbox_enabled is prepared for future SDK support.
    # Currently no-op, same as create_high_trust_options().
    if plan.sandbox_enabled:
        logger.debug(
            "PromptPlan specifies sandbox_enabled=True (not enforced until SDK adds support)"
        )

    # The SDK now exports ClaudeAgentOptions instead of ClaudeCodeOptions
    return sdk.ClaudeAgentOptions(**options_kwargs)
