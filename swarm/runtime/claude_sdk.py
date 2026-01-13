"""
claude_sdk.py - Unified Claude SDK adapter with deterministic options.

This module is the ONLY place that imports the Claude SDK package(s).
Supports both the official 'claude_agent_sdk' package and the legacy
'claude_code_sdk' package for backward compatibility.

It provides:
1. Clean imports with fallback handling
2. A single "options builder" that enforces High-Trust design
3. Helper functions for common SDK operations
4. StepSessionClient - Per-step session pattern with Work -> Finalize -> Route phases
5. Structured output schemas for HandoffEnvelope and RoutingSignal
6. NormalizedToolCall integration for unified tool call tracking

Usage:
    from swarm.runtime.claude_sdk import (
        SDK_AVAILABLE,
        create_high_trust_options,
        create_options_from_plan,
        query_with_options,
        get_sdk_module,
        get_sdk_module_name,  # For receipts: returns "claude_agent_sdk" or "claude_code_sdk"
        StepSessionClient,  # Per-step session orchestrator (Work -> Finalize -> Route)
        HANDOFF_ENVELOPE_SCHEMA,
        ROUTING_SIGNAL_SCHEMA,
        _dict_to_normalized_tool_call,  # Backward compatibility helper
        ALL_STANDARD_TOOLS,  # Set of standard Claude Code tools
        compute_disallowed_tools,  # Helper for deterministic tool restriction
    )

Design Principles:
    - Single import point for SDK
    - Options always set: cwd, permission_mode, system_prompt preset
    - Explicit tool surface policy
    - Project-only settings by default
    - High-trust tool policy: broad access with foot-gun blocking
    - Per-step sessions: Work -> Finalize -> Route in single hot context
    - Normalized tool calls for consistent receipt format across transports
"""

from __future__ import annotations

import logging

# Module logger
logger = logging.getLogger(__name__)

# =============================================================================
# Public API Re-exports from _claude_sdk
# =============================================================================

# SDK availability and module access
from swarm.runtime._claude_sdk.sdk_import import (
    SDK_AVAILABLE,
    _sdk_module,
    check_sdk_available,
    get_sdk_module,
    get_sdk_module_name,
    get_sdk_distribution,
    get_sdk_version,
)

# Options builder functions
from swarm.runtime._claude_sdk.options import (
    create_high_trust_options,
    create_options_from_plan,
)

# Query helpers
from swarm.runtime._claude_sdk.query import (
    query_with_options,
    query_simple,
)

# Structured output schemas
from swarm.runtime._claude_sdk.schemas import (
    HANDOFF_ENVELOPE_SCHEMA,
    ROUTING_SIGNAL_SCHEMA,
)

# Tool policy and restriction helpers
from swarm.runtime._claude_sdk.policy import (
    ALL_STANDARD_TOOLS,
    compute_disallowed_tools,
    is_blocked_command,
    create_tool_policy_hook,
)

# Hook factory functions
from swarm.runtime._claude_sdk.hooks import (
    create_dangerous_command_hook,
    create_telemetry_hook,
)

# Session management
from swarm.runtime._claude_sdk.session import (
    StepSessionClient,
)

# Telemetry data structures
from swarm.runtime._claude_sdk.telemetry import (
    TelemetryData,
)

# Compatibility helpers
from swarm.runtime._claude_sdk.compat import (
    _dict_to_normalized_tool_call,
)

# SDK surface shims (optional exports)
from swarm.runtime._claude_sdk.shims import (
    BaseHookInput,
    ContentBlock,
    HookCallback,
    HookContext,
    HookEvent,
    HookInput,
    HookJSONOutput,
    HookMatcher,
    MissingSdkFeatureError,
    PostToolUseHookInput,
    PreCompactHookInput,
    PreToolUseHookInput,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    AssistantMessage,
    Message,
    UserPromptSubmitHookInput,
    StopHookInput,
    SubagentStopHookInput,
    create_sdk_mcp_server,
    tool,
)

# =============================================================================
# Backward Compatibility Alias
# =============================================================================

# Preserve the old name for existing code that imports ClaudeSDKClient.
# New code should use StepSessionClient directly.
ClaudeSDKClient = StepSessionClient

# =============================================================================
# Backward Compatibility: ClaudeCodeOptions
# =============================================================================

# The SDK now exports ClaudeAgentOptions instead of ClaudeCodeOptions.
# For backward compatibility, we provide ClaudeCodeOptions as an alias.
# This is a lazy import pattern - the class is only accessed when needed.
def _get_claude_code_options_class():
    """Get the ClaudeCodeOptions class from the SDK module.
    
    Returns:
        The ClaudeAgentOptions class (or ClaudeCodeOptions for legacy SDKs).
    
    Raises:
        ImportError: If SDK is not available.
    """
    sdk = get_sdk_module()
    # The SDK now exports ClaudeAgentOptions instead of ClaudeCodeOptions
    if hasattr(sdk, "ClaudeAgentOptions"):
        return sdk.ClaudeAgentOptions
    if hasattr(sdk, "ClaudeCodeOptions"):
        return sdk.ClaudeCodeOptions
    raise MissingSdkFeatureError(
        "Claude SDK does not expose ClaudeAgentOptions or ClaudeCodeOptions."
    )

# For backward compatibility, provide ClaudeCodeOptions as a module-level attribute
# that lazily resolves to the SDK's ClaudeAgentOptions class.
class _ClaudeCodeOptionsProxy:
    """Proxy class for backward-compatible access to ClaudeCodeOptions."""
    
    def __getattr__(self, name):
        """Delegate all attribute access to the actual SDK class."""
        actual_class = _get_claude_code_options_class()
        return getattr(actual_class, name)
    
    def __call__(self, *args, **kwargs):
        """Delegate instantiation to the actual SDK class."""
        actual_class = _get_claude_code_options_class()
        return actual_class(*args, **kwargs)
    
    @property
    def __class__(self):
        """Return the actual class for isinstance checks."""
        return _get_claude_code_options_class()

# Create the proxy instance that will be used as ClaudeCodeOptions
ClaudeCodeOptions = _ClaudeCodeOptionsProxy()

# =============================================================================
# Public API Definition
# =============================================================================

__all__ = [
    # SDK availability
    "SDK_AVAILABLE",
    "_sdk_module",  # Backward compatibility: direct access to SDK module
    "check_sdk_available",
    "get_sdk_module",
    "get_sdk_module_name",
    "get_sdk_distribution",
    "get_sdk_version",
    # Options builder
    "create_high_trust_options",
    "create_options_from_plan",
    # Query helpers
    "query_with_options",
    "query_simple",
    # Structured output schemas
    "HANDOFF_ENVELOPE_SCHEMA",
    "ROUTING_SIGNAL_SCHEMA",
    # Tool policy
    "ALL_STANDARD_TOOLS",
    "compute_disallowed_tools",
    "is_blocked_command",
    "create_tool_policy_hook",
    # Hooks
    "create_dangerous_command_hook",
    "create_telemetry_hook",
    # Session management
    "StepSessionClient",
    # Telemetry
    "TelemetryData",  # Backward compatibility: telemetry data class
    # Compatibility
    "_dict_to_normalized_tool_call",
    "ClaudeSDKClient",  # Backward compatibility alias
    "ClaudeCodeOptions",  # Backward compatibility: proxy to ClaudeAgentOptions
    # SDK shims
    "MissingSdkFeatureError",
    "tool",
    "create_sdk_mcp_server",
    "Message",
    "UserMessage",
    "AssistantMessage",
    "SystemMessage",
    "ResultMessage",
    "StreamEvent",
    "ContentBlock",
    "TextBlock",
    "ThinkingBlock",
    "ToolUseBlock",
    "ToolResultBlock",
    "HookEvent",
    "HookMatcher",
    "HookCallback",
    "HookContext",
    "HookInput",
    "HookJSONOutput",
    "BaseHookInput",
    "PreToolUseHookInput",
    "PostToolUseHookInput",
    "UserPromptSubmitHookInput",
    "StopHookInput",
    "SubagentStopHookInput",
    "PreCompactHookInput",
]
