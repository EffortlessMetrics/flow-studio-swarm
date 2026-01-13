"""Optional SDK surface shims for offline-friendly imports.

These shims expose selected SDK symbols via the Flow Studio adapter without
re-implementing the SDK. When the SDK is not installed, type names resolve to
`Any` and runtime-only helpers raise a clear error.
"""

from __future__ import annotations

from typing import Any

from swarm.runtime._claude_sdk.sdk_import import SDK_AVAILABLE, get_sdk_module


class MissingSdkFeatureError(RuntimeError):
    """Raised when a requested SDK feature is not available."""


def _require_sdk_attr(name: str) -> Any:
    """Return an SDK attribute or raise a clear error if missing."""
    sdk = get_sdk_module()
    if not hasattr(sdk, name):
        raise MissingSdkFeatureError(
            f"Claude SDK does not expose '{name}' in this version. "
            "Update claude-agent-sdk and refresh vendor artifacts."
        )
    return getattr(sdk, name)


def _optional_sdk_attr(name: str, fallback: Any = Any) -> Any:
    """Return an SDK attribute or a fallback when unavailable."""
    if not SDK_AVAILABLE:
        return fallback
    sdk = get_sdk_module()
    return getattr(sdk, name, fallback)


def tool(*args: Any, **kwargs: Any) -> Any:
    """Pass-through to SDK tool() or raise if unavailable."""
    return _require_sdk_attr("tool")(*args, **kwargs)


def create_sdk_mcp_server(*args: Any, **kwargs: Any) -> Any:
    """Pass-through to SDK create_sdk_mcp_server() or raise if unavailable."""
    return _require_sdk_attr("create_sdk_mcp_server")(*args, **kwargs)


# Message/content-block types
Message = _optional_sdk_attr("Message", Any)
UserMessage = _optional_sdk_attr("UserMessage", Any)
AssistantMessage = _optional_sdk_attr("AssistantMessage", Any)
SystemMessage = _optional_sdk_attr("SystemMessage", Any)
ResultMessage = _optional_sdk_attr("ResultMessage", Any)
StreamEvent = _optional_sdk_attr("StreamEvent", Any)

ContentBlock = _optional_sdk_attr("ContentBlock", Any)
TextBlock = _optional_sdk_attr("TextBlock", Any)
ThinkingBlock = _optional_sdk_attr("ThinkingBlock", Any)
ToolUseBlock = _optional_sdk_attr("ToolUseBlock", Any)
ToolResultBlock = _optional_sdk_attr("ToolResultBlock", Any)

# Hook types
HookEvent = _optional_sdk_attr("HookEvent", Any)
HookMatcher = _optional_sdk_attr("HookMatcher", Any)
HookCallback = _optional_sdk_attr("HookCallback", Any)
HookContext = _optional_sdk_attr("HookContext", Any)
HookInput = _optional_sdk_attr("HookInput", Any)
HookJSONOutput = _optional_sdk_attr("HookJSONOutput", Any)
BaseHookInput = _optional_sdk_attr("BaseHookInput", Any)
PreToolUseHookInput = _optional_sdk_attr("PreToolUseHookInput", Any)
PostToolUseHookInput = _optional_sdk_attr("PostToolUseHookInput", Any)
UserPromptSubmitHookInput = _optional_sdk_attr("UserPromptSubmitHookInput", Any)
StopHookInput = _optional_sdk_attr("StopHookInput", Any)
SubagentStopHookInput = _optional_sdk_attr("SubagentStopHookInput", Any)
PreCompactHookInput = _optional_sdk_attr("PreCompactHookInput", Any)


__all__ = [
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
