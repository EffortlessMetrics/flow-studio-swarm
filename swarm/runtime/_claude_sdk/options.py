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

import inspect
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
    from swarm.spec.compiler.models import StepPlan
    from swarm.spec.types import PromptPlan

# Module logger
logger = logging.getLogger(__name__)

_ALLOWED_PERMISSION_MODES = {"default", "acceptEdits", "plan", "bypassPermissions"}
_PERMISSION_MODE_ALIASES = {
    "plan": "plan",
    "planmode": "plan",
    "plan_mode": "plan",
    "acceptedits": "acceptEdits",
    "accept_edits": "acceptEdits",
    "default": "default",
    "bypasspermissions": "bypassPermissions",
    "bypass_permissions": "bypassPermissions",
}


def normalize_permission_mode(value: Optional[str]) -> str:
    """Normalize permission mode values to Claude Agent SDK expectations."""
    if not value:
        return "bypassPermissions"
    stripped = value.strip()
    if stripped in _ALLOWED_PERMISSION_MODES:
        return stripped
    key = stripped.replace("-", "").replace("_", "").lower()
    return _PERMISSION_MODE_ALIASES.get(key, "bypassPermissions")


def _filter_options_kwargs(options_class: Any, options_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unsupported kwargs when SDK option fields differ across versions."""
    try:
        params = inspect.signature(options_class).parameters
    except (TypeError, ValueError):
        return options_kwargs

    accepted = set(params.keys())
    accepted.discard("self")
    filtered = {k: v for k, v in options_kwargs.items() if k in accepted}
    dropped = sorted(set(options_kwargs.keys()) - set(filtered.keys()))
    if dropped:
        logger.debug("Dropping unsupported ClaudeAgentOptions fields: %s", dropped)
    return filtered


def _build_options_kwargs(
    plan: Any,
    cwd: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Build kwargs for ClaudeAgentOptions from a plan-like object."""
    effective_cwd: Optional[str] = None
    if cwd is not None:
        effective_cwd = str(cwd)
    elif getattr(plan, "cwd", None):
        effective_cwd = str(plan.cwd)

    system_prompt: Dict[str, Any] = {
        "type": "preset",
        "preset": SYSTEM_PROMPT_PRESET,
    }
    if getattr(plan, "system_append", ""):
        system_prompt["append"] = plan.system_append

    permission_mode = normalize_permission_mode(getattr(plan, "permission_mode", None))

    options_kwargs: Dict[str, Any] = {
        "permission_mode": permission_mode,
        "setting_sources": ["project"],
        "system_prompt": system_prompt,
    }

    if effective_cwd:
        options_kwargs["cwd"] = effective_cwd
    else:
        logger.warning(
            "Options created without cwd and plan.cwd is empty - "
            "execution may fail or use unexpected working directory"
        )

    model = getattr(plan, "model", None)
    if model:
        options_kwargs["model"] = model

    max_turns = getattr(plan, "max_turns", None)
    if max_turns:
        options_kwargs["max_turns"] = max_turns

    allowed_tools = getattr(plan, "allowed_tools", None)
    if allowed_tools is not None:  # Use 'is not None' to properly handle empty list []
        options_kwargs["allowed_tools"] = allowed_tools
        disallowed = compute_disallowed_tools(allowed_tools)
        if disallowed:  # Empty disallowed list is valid - means no tools blocked
            options_kwargs["disallowed_tools"] = disallowed
        logger.debug(
            "Plan specifies allowed_tools=%s, computed disallowed_tools=%s",
            allowed_tools,
            disallowed,
        )

    output_schema = getattr(plan, "output_schema", None)
    if output_schema:
        options_kwargs["output_format"] = {
            "type": "json_schema",
            "schema": output_schema,
        }

    if hasattr(plan, "sandbox_enabled"):
        options_kwargs["sandbox"] = {"enabled": bool(plan.sandbox_enabled)}

    return options_kwargs


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

    sdk = get_sdk_module()
    options_kwargs = _build_options_kwargs(plan, cwd)
    options_kwargs = _filter_options_kwargs(sdk.ClaudeAgentOptions, options_kwargs)
    return sdk.ClaudeAgentOptions(**options_kwargs)


def step_plan_to_agent_options(
    step_plan: "StepPlan",
    cwd: Optional[Union[str, Path]] = None,
) -> Any:
    """Create ClaudeAgentOptions from a compiled StepPlan."""
    from swarm.runtime._claude_sdk.sdk_import import SDK_AVAILABLE, _sdk_import_error

    if not SDK_AVAILABLE:
        raise RuntimeError(
            f"Claude SDK not available: {_sdk_import_error}. "
            "Install with: pip install claude-code-sdk"
        )

    sdk = get_sdk_module()
    options_kwargs = _build_options_kwargs(step_plan, cwd)
    options_kwargs = _filter_options_kwargs(sdk.ClaudeAgentOptions, options_kwargs)
    return sdk.ClaudeAgentOptions(**options_kwargs)
