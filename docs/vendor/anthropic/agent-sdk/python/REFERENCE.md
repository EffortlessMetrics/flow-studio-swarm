# Agent SDK Reference - Python

This is a vendored upstream reference. For Flow Studio's adapter API and supported subset, see docs/reference/CLAUDE_AGENT_SDK_ADAPTER_CONTRACT.md.

Vendored from: https://docs.anthropic.com/en/docs/agent-sdk/python
SDK version: `claude-agent-sdk 0.1.19`
Snapshot date: 2026-01-13

Complete API reference for the Python Agent SDK, including all functions, types, and classes exposed by `claude_agent_sdk`.

## Installation

```bash
pip install claude-agent-sdk
```

| Property | Type | Default | Description |
| :-- | :-- | :-- | :-- |
| `tools` | `list[str] | ToolsPreset | None` | `None` | Base tool set passed to the CLI (`--tools`). Use `{"type": "preset", "preset": "claude_code"}` for default toolset. |
| `allowed_tools` | `list[str]` | `[]` | List of allowed tool names |
| `system_prompt` | `str | SystemPromptPreset | None` | `None` | System prompt configuration |
| `mcp_servers` | `dict[str, McpServerConfig] | str | Path` | `{}` | MCP server configurations or path to config file |
| `permission_mode` | `PermissionMode | None` | `None` | Permission mode for tool usage |
| `continue_conversation` | `bool` | `False` | Continue the most recent conversation |
| `resume` | `str | None` | `None` | Session ID to resume |
| `max_turns` | `int | None` | `None` | Maximum conversation turns |
| `max_budget_usd` | `float | None` | `None` | Budget cap in USD for a session |
| `disallowed_tools` | `list[str]` | `[]` | List of disallowed tool names |
| `model` | `str | None` | `None` | Claude model to use |
| `fallback_model` | `str | None` | `None` | Model to fall back to if the primary model is unavailable |
| `betas` | `list[SdkBeta]` | `[]` | Beta feature flags |
| `permission_prompt_tool_name` | `str | None` | `None` | MCP tool name for permission prompts |
| `cwd` | `str | Path | None` | `None` | Current working directory |
| `cli_path` | `str | Path | None` | `None` | Path to the Claude Code CLI binary |
| `settings` | `str | None` | `None` | Settings JSON string or path to settings file |
| `add_dirs` | `list[str | Path]` | `[]` | Additional directories Claude can access |
| `env` | `dict[str, str]` | `{}` | Environment variables |
| `extra_args` | `dict[str, str | None]` | `{}` | Additional CLI arguments (for flags like `replay-user-messages`) |
| `max_buffer_size` | `int | None` | `None` | Maximum bytes when buffering CLI stdout |
| `debug_stderr` | `Any` | `sys.stderr` | Deprecated debug output sink |
| `stderr` | `Callable[[str], None] | None` | `None` | Callback for stderr output from CLI |
| `can_use_tool` | `CanUseTool | None` | `None` | Tool permission callback function |
| `hooks` | `dict[HookEvent, list[HookMatcher]] | None` | `None` | Hook configurations for intercepting events |
| `user` | `str | None` | `None` | User identifier |
| `include_partial_messages` | `bool` | `False` | Include partial message streaming events (`StreamEvent`) |
| `fork_session` | `bool` | `False` | When resuming, fork to a new session ID instead of continuing |
| `agents` | `dict[str, AgentDefinition] | None` | `None` | Programmatically defined subagents |
| `setting_sources` | `list[SettingSource] | None` | `None` | Control which filesystem settings to load |
| `sandbox` | `SandboxSettings | None` | `None` | Configure sandbox behavior programmatically |
| `plugins` | `list[SdkPluginConfig]` | `[]` | Load custom plugins from local paths |
| `max_thinking_tokens` | `int | None` | `None` | Max tokens for thinking blocks |
| `output_format` | `dict[str, Any] | None` | `None` | Structured output format (JSON schema) |
| `enable_file_checkpointing` | `bool` | `False` | Track file changes for `rewind_files()` |

### `OutputFormat`

Configuration for structured output validation.

```python
class OutputFormat(TypedDict):
    type: Literal["json_schema"]
    schema: dict[str, Any]
```

### `SystemPromptPreset`

Configuration for using Claude Code's preset system prompt with optional additions.

```python
class SystemPromptPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
    append: NotRequired[str]
```

### `ToolsPreset`

Preset tool configuration passed via `ClaudeAgentOptions.tools`.

```python
class ToolsPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
```

### `SettingSource`

Controls which filesystem-based configuration sources the SDK loads settings from.

```python
SettingSource = Literal["user", "project", "local"]
```

Default behavior:
- When `setting_sources` is omitted or `None`, the SDK does not load filesystem settings.

Settings precedence (highest to lowest):
1. Local settings (`.claude/settings.local.json`)
2. Project settings (`.claude/settings.json`)
3. User settings (`~/.claude/settings.json`)

### `SdkBeta`

Beta feature flags (forwarded to the CLI).

```python
SdkBeta = Literal["context-1m-2025-08-07"]
```

### `AgentDefinition`

Configuration for a subagent defined programmatically.

```python
@dataclass
class AgentDefinition:
    description: str
    prompt: str
    tools: list[str] | None = None
    model: Literal["sonnet", "opus", "haiku", "inherit"] | None = None
```

### `PermissionMode`

Permission modes for controlling tool execution.

```python
PermissionMode = Literal[
    "default",
    "acceptEdits",
    "plan",
    "bypassPermissions"
]
```

### `PermissionRuleValue`

```python
@dataclass
class PermissionRuleValue:
    tool_name: str
    rule_content: str | None = None
```

### `PermissionUpdate`

```python
PermissionUpdateDestination = Literal[
    "userSettings",
    "projectSettings",
    "localSettings",
    "session"
]

PermissionBehavior = Literal["allow", "deny", "ask"]

@dataclass
class PermissionUpdate:
    type: Literal[
        "addRules",
        "replaceRules",
        "removeRules",
        "setMode",
        "addDirectories",
        "removeDirectories",
    ]
    rules: list[PermissionRuleValue] | None = None
    behavior: PermissionBehavior | None = None
    mode: PermissionMode | None = None
    directories: list[str] | None = None
    destination: PermissionUpdateDestination | None = None

    def to_dict(self) -> dict[str, Any]
```

### `PermissionResultAllow`

```python
@dataclass
class PermissionResultAllow:
    behavior: Literal["allow"] = "allow"
    updated_input: dict[str, Any] | None = None
    updated_permissions: list[PermissionUpdate] | None = None
```

### `PermissionResultDeny`

```python
@dataclass
class PermissionResultDeny:
    behavior: Literal["deny"] = "deny"
    message: str = ""
    interrupt: bool = False
```

### `PermissionResult`

```python
PermissionResult = PermissionResultAllow | PermissionResultDeny
```

### `ToolPermissionContext`

```python
@dataclass
class ToolPermissionContext:
    signal: Any | None = None
    suggestions: list[PermissionUpdate] = field(default_factory=list)
```

### `CanUseTool`

```python
CanUseTool = Callable[
    [str, dict[str, Any], ToolPermissionContext],
    Awaitable[PermissionResult]
]
```

### `McpSdkServerConfig`

```python
class McpSdkServerConfig(TypedDict):
    type: Literal["sdk"]
    name: str
    instance: Any
```

### `McpServerConfig`

```python
McpServerConfig = (
    McpStdioServerConfig
    | McpSSEServerConfig
    | McpHttpServerConfig
    | McpSdkServerConfig
)
```

#### `McpStdioServerConfig`

```python
class McpStdioServerConfig(TypedDict):
    type: NotRequired[Literal["stdio"]]
    command: str
    args: NotRequired[list[str]]
    env: NotRequired[dict[str, str]]
```

#### `McpSSEServerConfig`

```python
class McpSSEServerConfig(TypedDict):
    type: Literal["sse"]
    url: str
    headers: NotRequired[dict[str, str]]
```

#### `McpHttpServerConfig`

```python
class McpHttpServerConfig(TypedDict):
    type: Literal["http"]
    url: str
    headers: NotRequired[dict[str, str]]
```

### `SdkPluginConfig`

```python
class SdkPluginConfig(TypedDict):
    type: Literal["local"]
    path: str
```

### `Transport`

Low-level transport interface for custom connections.

```python
class Transport(ABC):
    async def connect(self) -> None
    async def write(self, data: str) -> None
    def read_messages(self) -> AsyncIterator[dict[str, Any]]
    async def close(self) -> None
    def is_ready(self) -> bool
    async def end_input(self) -> None
```

### `SandboxSettings`

Configuration for sandbox behavior.

```python
class SandboxSettings(TypedDict, total=False):
    enabled: bool
    autoAllowBashIfSandboxed: bool
    excludedCommands: list[str]
    allowUnsandboxedCommands: bool
    network: SandboxNetworkConfig
    ignoreViolations: SandboxIgnoreViolations
    enableWeakerNestedSandbox: bool
```

See [Sandbox Configuration](#sandbox-configuration) for details and examples.

## Message Types

### `Message`

Union type of all possible messages.

```python
Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent
```

### `UserMessage`

User input message.

```python
@dataclass
class UserMessage:
    content: str | list[ContentBlock]
    uuid: str | None = None
    parent_tool_use_id: str | None = None
```

### `AssistantMessage`

Assistant response message with content blocks.

```python
@dataclass
class AssistantMessage:
    content: list[ContentBlock]
    model: str
    parent_tool_use_id: str | None = None
    error: AssistantMessageError | None = None
```

### `SystemMessage`

System message with metadata.

```python
@dataclass
class SystemMessage:
    subtype: str
    data: dict[str, Any]
```

### `ResultMessage`

Final result message with cost and usage information.

```python
@dataclass
class ResultMessage:
    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    total_cost_usd: float | None = None
    usage: dict[str, Any] | None = None
    result: str | None = None
    structured_output: Any = None
```

### `StreamEvent`

Partial streaming event (emitted when `include_partial_messages=True`).

```python
@dataclass
class StreamEvent:
    uuid: str
    session_id: str
    event: dict[str, Any]
    parent_tool_use_id: str | None = None
```

## Content Block Types

### `ContentBlock`

Union type of all content blocks.

```python
ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock
```

### `TextBlock`

```python
@dataclass
class TextBlock:
    text: str
```

### `ThinkingBlock`

```python
@dataclass
class ThinkingBlock:
    thinking: str
    signature: str
```

### `ToolUseBlock`

```python
@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
```

### `ToolResultBlock`

```python
@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: str | list[dict[str, Any]] | None = None
    is_error: bool | None = None
```

## Error Types

### `ClaudeSDKError`

Base exception class for all SDK errors.

```python
class ClaudeSDKError(Exception):
    pass
```

### `CLIConnectionError`

Raised when connection to Claude Code fails.

```python
class CLIConnectionError(ClaudeSDKError):
    pass
```

### `CLINotFoundError`

Raised when Claude Code CLI is not installed or not found.

```python
class CLINotFoundError(CLIConnectionError):
    def __init__(self, message: str = "Claude Code not found", cli_path: str | None = None)
```

### `ProcessError`

Raised when the Claude Code process fails.

```python
class ProcessError(ClaudeSDKError):
    def __init__(self, message: str, exit_code: int | None = None, stderr: str | None = None)
```

### `CLIJSONDecodeError`

Raised when JSON parsing fails.

```python
class CLIJSONDecodeError(ClaudeSDKError):
    def __init__(self, line: str, original_error: Exception)
```

## Hook Types

For a comprehensive guide on using hooks with examples and common patterns, see the Hooks guide.

### `HookEvent`

Supported hook event types. The Python SDK does not support SessionStart, SessionEnd, or Notification hooks.

```python
HookEvent = Literal[
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "PreCompact"
]
```

### `BaseHookInput`

```python
class BaseHookInput(TypedDict):
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: NotRequired[str]
```

### `PreToolUseHookInput`

```python
class PreToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
```

### `PostToolUseHookInput`

```python
class PostToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: Any
```

### `UserPromptSubmitHookInput`

```python
class UserPromptSubmitHookInput(BaseHookInput):
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str
```

### `StopHookInput`

```python
class StopHookInput(BaseHookInput):
    hook_event_name: Literal["Stop"]
    stop_hook_active: bool
```

### `SubagentStopHookInput`

```python
class SubagentStopHookInput(BaseHookInput):
    hook_event_name: Literal["SubagentStop"]
    stop_hook_active: bool
```

### `PreCompactHookInput`

```python
class PreCompactHookInput(BaseHookInput):
    hook_event_name: Literal["PreCompact"]
    trigger: Literal["manual", "auto"]
    custom_instructions: str | None
```

### `HookInput`

```python
HookInput = (
    PreToolUseHookInput
    | PostToolUseHookInput
    | UserPromptSubmitHookInput
    | StopHookInput
    | SubagentStopHookInput
    | PreCompactHookInput
)
```

### `HookJSONOutput`

Hook callbacks return `HookJSONOutput`, which is either async or sync output.

```python
class AsyncHookJSONOutput(TypedDict):
    async_: Literal[True]
    asyncTimeout: NotRequired[int]
```

```python
class SyncHookJSONOutput(TypedDict, total=False):
    continue_: bool
    suppressOutput: bool
    stopReason: str
    decision: Literal["block"]
    systemMessage: str
    reason: str
    hookSpecificOutput: dict[str, Any]
```

Notes:
- Use `async_` and `continue_` (with underscores) in Python; they are converted to `async` and `continue` for the CLI.

### `HookJSONOutput`

```python
HookJSONOutput = AsyncHookJSONOutput | SyncHookJSONOutput
```

### `HookContext`

```python
class HookContext(TypedDict):
    signal: Any | None
```

### `HookCallback`

```python
HookCallback = Callable[
    [HookInput, str | None, HookContext],
    Awaitable[HookJSONOutput]
]
```

### `HookMatcher`

```python
@dataclass
class HookMatcher:
    matcher: str | None = None
    hooks: list[HookCallback] = field(default_factory=list)
    timeout: float | None = None
```

### Hook Usage Example

```python
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, HookContext
from typing import Any

async def validate_bash_command(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    if input_data["tool_name"] == "Bash":
        command = input_data["tool_input"].get("command", "")
        if "rm -rf /" in command:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Dangerous command blocked"
                }
            }
    return {}

async def log_tool_use(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    print(f"Tool used: {input_data.get('tool_name')}")
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[validate_bash_command], timeout=120),
            HookMatcher(hooks=[log_tool_use])
        ],
        "PostToolUse": [
            HookMatcher(hooks=[log_tool_use])
        ]
    }
)

async for message in query(
    prompt="Analyze this codebase",
    options=options
):
    print(message)
```

## Tool Input/Output Types

Documentation of input/output schemas for all built-in Claude Code tools. While the Python SDK does not export these as types, they represent the structure of tool inputs and outputs in messages.

### Task

**Tool name:** `Task`

**Input:**

```python
{
    "description": str,
    "prompt": str,
    "subagent_type": str
}
```

**Output:**

```python
{
    "result": str,
    "usage": dict | None,
    "total_cost_usd": float | None,
    "duration_ms": int | None
}
```

### AskUserQuestion

**Tool name:** `AskUserQuestion`

Asks the user clarifying questions during execution.

**Input:**

```python
{
    "questions": [
        {
            "question": str,
            "header": str,
            "options": [
                {
                    "label": str,
                    "description": str
                }
            ],
            "multiSelect": bool
        }
    ],
    "answers": dict | None
}
```

**Output:**

```python
{
    "questions": [
        {
            "question": str,
            "header": str,
            "options": [{"label": str, "description": str}],
            "multiSelect": bool
        }
    ],
    "answers": dict[str, str]
}
```

### Bash

**Tool name:** `Bash`

**Input:**

```python
{
    "command": str,
    "timeout": int | None,
    "description": str | None,
    "run_in_background": bool | None
}
```

**Output:**

```python
{
    "output": str,
    "exitCode": int,
    "killed": bool | None,
    "shellId": str | None
}
```

### Edit

**Tool name:** `Edit`

**Input:**

```python
{
    "file_path": str,
    "old_string": str,
    "new_string": str,
    "replace_all": bool | None
}
```

**Output:**

```python
{
    "message": str,
    "replacements": int,
    "file_path": str
}
```

### Read

**Tool name:** `Read`

**Input:**

```python
{
    "file_path": str,
    "offset": int | None,
    "limit": int | None
}
```

**Output (Text files):**

```python
{
    "content": str,
    "total_lines": int,
    "lines_returned": int
}
```

**Output (Images):**

```python
{
    "image": str,
    "mime_type": str,
    "file_size": int
}
```

### Write

**Tool name:** `Write`

**Input:**

```python
{
    "file_path": str,
    "content": str
}
```

**Output:**

```python
{
    "message": str,
    "bytes_written": int,
    "file_path": str
}
```

### Glob

**Tool name:** `Glob`

**Input:**

```python
{
    "pattern": str,
    "path": str | None
}
```

**Output:**

```python
{
    "matches": list[str],
    "count": int,
    "search_path": str
}
```

### Grep

**Tool name:** `Grep`

**Input:**

```python
{
    "pattern": str,
    "path": str | None,
    "glob": str | None,
    "type": str | None,
    "output_mode": str | None,
    "-i": bool | None,
    "-n": bool | None,
    "-B": int | None,
    "-A": int | None,
    "-C": int | None,
    "head_limit": int | None,
    "multiline": bool | None
}
```

**Output (content mode):**

```python
{
    "matches": [
        {
            "file": str,
            "line_number": int | None,
            "line": str,
            "before_context": list[str] | None,
            "after_context": list[str] | None
        }
    ],
    "total_matches": int
}
```

**Output (files_with_matches mode):**

```python
{
    "files": list[str],
    "count": int
}
```

### NotebookEdit

**Tool name:** `NotebookEdit`

**Input:**

```python
{
    "notebook_path": str,
    "cell_id": str | None,
    "new_source": str,
    "cell_type": "code" | "markdown" | None,
    "edit_mode": "replace" | "insert" | "delete" | None
}
```

**Output:**

```python
{
    "message": str,
    "edit_type": "replaced" | "inserted" | "deleted",
    "cell_id": str | None,
    "total_cells": int
}
```

### WebFetch

**Tool name:** `WebFetch`

**Input:**

```python
{
    "url": str,
    "prompt": str
}
```

**Output:**

```python
{
    "response": str,
    "url": str,
    "final_url": str | None,
    "status_code": int | None
}
```

### WebSearch

**Tool name:** `WebSearch`

**Input:**

```python
{
    "query": str,
    "allowed_domains": list[str] | None,
    "blocked_domains": list[str] | None
}
```

**Output:**

```python
{
    "results": [
        {
            "title": str,
            "url": str,
            "snippet": str,
            "metadata": dict | None
        }
    ],
    "total_results": int,
    "query": str
}
```

### TodoWrite

**Tool name:** `TodoWrite`

**Input:**

```python
{
    "todos": [
        {
            "content": str,
            "status": "pending" | "in_progress" | "completed",
            "activeForm": str
        }
    ]
}
```

**Output:**

```python
{
    "message": str,
    "stats": {
        "total": int,
        "pending": int,
        "in_progress": int,
        "completed": int
    }
}
```

### BashOutput

**Tool name:** `BashOutput`

**Input:**

```python
{
    "bash_id": str,
    "filter": str | None
}
```

**Output:**

```python
{
    "output": str,
    "status": "running" | "completed" | "failed",
    "exitCode": int | None
}
```

### KillBash

**Tool name:** `KillBash`

**Input:**

```python
{
    "shell_id": str
}
```

**Output:**

```python
{
    "message": str,
    "shell_id": str
}
```

### ExitPlanMode

**Tool name:** `ExitPlanMode`

**Input:**

```python
{
    "plan": str
}
```

**Output:**

```python
{
    "message": str,
    "approved": bool | None
}
```

### ListMcpResources

**Tool name:** `ListMcpResources`

**Input:**

```python
{
    "server": str | None
}
```

**Output:**

```python
{
    "resources": [
        {
            "uri": str,
            "name": str,
            "description": str | None,
            "mimeType": str | None,
            "server": str
        }
    ],
    "total": int
}
```

### ReadMcpResource

**Tool name:** `ReadMcpResource`

**Input:**

```python
{
    "server": str,
    "uri": str
}
```

**Output:**

```python
{
    "contents": [
        {
            "uri": str,
            "mimeType": str | None,
            "text": str | None,
            "blob": str | None
        }
    ],
    "server": str
}
```

## Advanced Features with ClaudeSDKClient

### Building a Continuous Conversation Interface

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock
import asyncio

class ConversationSession:
    """Maintains a single conversation session with Claude."""

    def __init__(self, options: ClaudeAgentOptions | None = None):
        self.client = ClaudeSDKClient(options)
        self.turn_count = 0

    async def start(self):
        await self.client.connect()
        print("Starting conversation session. Claude will remember context.")
        print("Commands: 'exit' to quit, 'interrupt' to stop current task, 'new' for new session")

        while True:
            user_input = input(f"\n[Turn {self.turn_count + 1}] You: ")

            if user_input.lower() == "exit":
                break
            if user_input.lower() == "interrupt":
                await self.client.interrupt()
                print("Task interrupted!")
                continue
            if user_input.lower() == "new":
                await self.client.disconnect()
                await self.client.connect()
                self.turn_count = 0
                print("Started new conversation session (previous context cleared)")
                continue

            await self.client.query(user_input)
            self.turn_count += 1

            print(f"[Turn {self.turn_count}] Claude: ", end="")
            async for message in self.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="")
            print()

        await self.client.disconnect()
        print(f"Conversation ended after {self.turn_count} turns.")

async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits"
    )
    session = ConversationSession(options)
    await session.start()

asyncio.run(main())
```

## Sandbox Configuration

### `SandboxSettings`

Configuration for sandbox behavior. Use this to enable command sandboxing and configure network restrictions programmatically.

```python
class SandboxSettings(TypedDict, total=False):
    enabled: bool
    autoAllowBashIfSandboxed: bool
    excludedCommands: list[str]
    allowUnsandboxedCommands: bool
    network: SandboxNetworkConfig
    ignoreViolations: SandboxIgnoreViolations
    enableWeakerNestedSandbox: bool
```

| Property | Type | Default | Description |
| :-- | :-- | :-- | :-- |
| `enabled` | `bool` | `False` | Enable sandbox mode for command execution |
| `autoAllowBashIfSandboxed` | `bool` | `True` | Auto-approve bash commands when sandboxed |
| `excludedCommands` | `list[str]` | `[]` | Commands that always bypass sandbox restrictions |
| `allowUnsandboxedCommands` | `bool` | `True` | Allow the model to request unsandboxed execution via `dangerouslyDisableSandbox` |
| `network` | `SandboxNetworkConfig` | `None` | Network-specific sandbox configuration |
| `ignoreViolations` | `SandboxIgnoreViolations` | `None` | Configure which sandbox violations to ignore |
| `enableWeakerNestedSandbox` | `bool` | `False` | Enable weaker nested sandbox for compatibility |

Note: Filesystem and network access restrictions are not configured via sandbox settings. Instead, they are derived from permission rules:
- Filesystem read restrictions: Read deny rules
- Filesystem write restrictions: Edit allow/deny rules
- Network restrictions: WebFetch allow/deny rules

#### Example usage

```python
from claude_agent_sdk import query, ClaudeAgentOptions, SandboxSettings

sandbox_settings: SandboxSettings = {
    "enabled": True,
    "autoAllowBashIfSandboxed": True,
    "excludedCommands": ["docker"],
    "network": {
        "allowLocalBinding": True,
        "allowUnixSockets": ["/var/run/docker.sock"]
    }
}

async for message in query(
    prompt="Build and test my project",
    options=ClaudeAgentOptions(sandbox=sandbox_settings)
):
    print(message)
```

### `SandboxNetworkConfig`

```python
class SandboxNetworkConfig(TypedDict, total=False):
    allowLocalBinding: bool
    allowUnixSockets: list[str]
    allowAllUnixSockets: bool
    httpProxyPort: int
    socksProxyPort: int
```

### `SandboxIgnoreViolations`

```python
class SandboxIgnoreViolations(TypedDict, total=False):
    file: list[str]
    network: list[str]
```

### Permissions Fallback for Unsandboxed Commands

When `allowUnsandboxedCommands` is enabled, the model can request to run commands outside the sandbox by setting `dangerouslyDisableSandbox: True` in the tool input. These requests fall back to the existing permissions system, meaning your `can_use_tool` handler will be invoked.

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

async def can_use_tool(tool: str, input: dict, context: ToolPermissionContext):
    if tool == "Bash" and input.get("dangerouslyDisableSandbox"):
        if is_command_authorized(input.get("command")):
            return PermissionResultAllow(updated_input=input)
        return PermissionResultDeny(message="Unsandboxed command denied", interrupt=True)
    return PermissionResultAllow(updated_input=input)

async def main():
    async for message in query(
        prompt="Deploy my application",
        options=ClaudeAgentOptions(
            sandbox={
                "enabled": True,
                "allowUnsandboxedCommands": True
            },
            permission_mode="default",
            can_use_tool=can_use_tool
        )
    ):
        print(message)
```

## See also

- Python SDK guide: /docs/en/agent-sdk/python
- SDK overview: /docs/en/agent-sdk/overview
- TypeScript SDK reference: /docs/en/agent-sdk/typescript
- CLI reference: https://code.claude.com/docs/en/cli-reference
- Common workflows: https://code.claude.com/docs/en/common-workflows

### Real-time Progress Monitoring

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ToolUseBlock,
    ToolResultBlock,
    TextBlock
)
import asyncio

async def monitor_progress():
    options = ClaudeAgentOptions(
        allowed_tools=["Write", "Bash"],
        permission_mode="acceptEdits"
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Create 5 Python files with different sorting algorithms"
        )

        async for message in client.receive_messages():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        if block.name == "Write":
                            file_path = block.input.get("file_path", "")
                            print(f"Creating: {file_path}")
                    elif isinstance(block, ToolResultBlock):
                        print("Tool execution completed")
                    elif isinstance(block, TextBlock):
                        print(f"Claude says: {block.text[:100]}...")

            if hasattr(message, "subtype") and message.subtype in ["success", "error"]:
                print("Task completed")
                break

asyncio.run(monitor_progress())
```

## Example Usage

### Basic file operations (using query)

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ToolUseBlock
import asyncio

async def create_project():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        cwd="/home/user/project"
    )

    async for message in query(
        prompt="Create a Python project structure with setup.py",
        options=options
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"Using tool: {block.name}")

asyncio.run(create_project())
```

### Error handling

```python
from claude_agent_sdk import (
    query,
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError
)

try:
    async for message in query(prompt="Hello"):
        print(message)
except CLINotFoundError:
    print("Please install Claude Code: npm install -g @anthropic-ai/claude-code")
except ProcessError as e:
    print(f"Process failed with exit code: {e.exit_code}")
except CLIJSONDecodeError as e:
    print(f"Failed to parse response: {e}")
```

### Streaming mode with client

```python
from claude_agent_sdk import ClaudeSDKClient
import asyncio

async def interactive_session():
    async with ClaudeSDKClient() as client:
        await client.query("What's the weather like?")

        async for msg in client.receive_response():
            print(msg)

        await client.query("Tell me more about that")

        async for msg in client.receive_response():
            print(msg)

asyncio.run(interactive_session())
```

### Using custom tools with ClaudeSDKClient

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock
)
import asyncio
from typing import Any

@tool("calculate", "Perform mathematical calculations", {"expression": str})
async def calculate(args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = eval(args["expression"], {"__builtins__": {}})
        return {
            "content": [{
                "type": "text",
                "text": f"Result: {result}"
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: {str(e)}"
            }],
            "is_error": True
        }

@tool("get_time", "Get current time", {})
async def get_time(args: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "content": [{
            "type": "text",
            "text": f"Current time: {current_time}"
        }]
    }

async def main():
    my_server = create_sdk_mcp_server(
        name="utilities",
        version="1.0.0",
        tools=[calculate, get_time]
    )

    options = ClaudeAgentOptions(
        mcp_servers={"utils": my_server},
        allowed_tools=[
            "mcp__utils__calculate",
            "mcp__utils__get_time"
        ]
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("What's 123 * 456?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Calculation: {block.text}")

        await client.query("What time is it now?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Time: {block.text}")

asyncio.run(main())
```

### Using Hooks for Behavior Modification

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    HookContext
)
import asyncio
from typing import Any

async def pre_tool_logger(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    tool_name = input_data.get("tool_name", "unknown")
    print(f"[PRE-TOOL] About to use: {tool_name}")

    if tool_name == "Bash" and "rm -rf" in str(input_data.get("tool_input", {})):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked"
            }
        }
    return {}

async def post_tool_logger(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    tool_name = input_data.get("tool_name", "unknown")
    print(f"[POST-TOOL] Completed: {tool_name}")
    return {}

async def user_prompt_modifier(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    original_prompt = input_data.get("prompt", "")
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"[{timestamp}] {original_prompt}"
        }
    }

async def main():
    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [
                HookMatcher(hooks=[pre_tool_logger]),
                HookMatcher(matcher="Bash", hooks=[pre_tool_logger])
            ],
            "PostToolUse": [
                HookMatcher(hooks=[post_tool_logger])
            ],
            "UserPromptSubmit": [
                HookMatcher(hooks=[user_prompt_modifier])
            ]
        },
        allowed_tools=["Read", "Write", "Bash"]
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("List files in current directory")

        async for message in client.receive_response():
            pass

asyncio.run(main())
```

## Types

### `SdkMcpTool`

Definition for an SDK MCP tool created with the `@tool` decorator.

```python
@dataclass
class SdkMcpTool(Generic[T]):
    name: str
    description: str
    input_schema: type[T] | dict[str, Any]
    handler: Callable[[T], Awaitable[dict[str, Any]]]
```

| Property | Type | Description |
| :-- | :-- | :-- |
| `name` | `str` | Unique identifier for the tool |
| `description` | `str` | Human-readable description |
| `input_schema` | `type[T] | dict[str, Any]` | Schema for input validation |
| `handler` | `Callable[[T], Awaitable[dict[str, Any]]]` | Async function that handles tool execution |

### `ClaudeAgentOptions`

Configuration dataclass for Claude Code queries.

```python
@dataclass
class ClaudeAgentOptions:
    tools: list[str] | ToolsPreset | None = None
    allowed_tools: list[str] = field(default_factory=list)
    system_prompt: str | SystemPromptPreset | None = None
    mcp_servers: dict[str, McpServerConfig] | str | Path = field(default_factory=dict)
    permission_mode: PermissionMode | None = None
    continue_conversation: bool = False
    resume: str | None = None
    max_turns: int | None = None
    max_budget_usd: float | None = None
    disallowed_tools: list[str] = field(default_factory=list)
    model: str | None = None
    fallback_model: str | None = None
    betas: list[SdkBeta] = field(default_factory=list)
    permission_prompt_tool_name: str | None = None
    cwd: str | Path | None = None
    cli_path: str | Path | None = None
    settings: str | None = None
    add_dirs: list[str | Path] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    extra_args: dict[str, str | None] = field(default_factory=dict)
    max_buffer_size: int | None = None
    debug_stderr: Any = sys.stderr  # Deprecated
    stderr: Callable[[str], None] | None = None
    can_use_tool: CanUseTool | None = None
    hooks: dict[HookEvent, list[HookMatcher]] | None = None
    user: str | None = None
    include_partial_messages: bool = False
    fork_session: bool = False
    agents: dict[str, AgentDefinition] | None = None
    setting_sources: list[SettingSource] | None = None
    sandbox: SandboxSettings | None = None
    plugins: list[SdkPluginConfig] = field(default_factory=list)
    max_thinking_tokens: int | None = None
    output_format: dict[str, Any] | None = None
    enable_file_checkpointing: bool = False
```

#### Example - Advanced permission control

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext
)

async def custom_permission_handler(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    if tool_name == "Write" and input_data.get("file_path", "").startswith("/system/"):
        return PermissionResultDeny(
            message="System directory write not allowed",
            interrupt=True
        )

    if tool_name in ["Write", "Edit"] and "config" in input_data.get("file_path", ""):
        safe_path = f"./sandbox/{input_data['file_path']}"
        return PermissionResultAllow(
            updated_input={**input_data, "file_path": safe_path}
        )

    return PermissionResultAllow(updated_input=input_data)

async def main():
    options = ClaudeAgentOptions(
        can_use_tool=custom_permission_handler,
        allowed_tools=["Read", "Write", "Edit"]
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Update the system config file")

        async for message in client.receive_response():
            print(message)

asyncio.run(main())
```

#### Example - Using interrupts

```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async def interruptible_task():
    options = ClaudeAgentOptions(
        allowed_tools=["Bash"],
        permission_mode="acceptEdits"
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Count from 1 to 100 slowly")

        await asyncio.sleep(2)

        await client.interrupt()
        print("Task interrupted!")

        await client.query("Just say hello instead")

        async for message in client.receive_response():
            pass

asyncio.run(interruptible_task())
```

#### Example - Streaming input with ClaudeSDKClient

```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def message_stream():
    """Generate messages dynamically."""
    yield {"type": "text", "text": "Analyze the following data:"}
    await asyncio.sleep(0.5)
    yield {"type": "text", "text": "Temperature: 25 deg C"}
    await asyncio.sleep(0.5)
    yield {"type": "text", "text": "Humidity: 60%"}
    await asyncio.sleep(0.5)
    yield {"type": "text", "text": "What patterns do you see?"}

async def main():
    async with ClaudeSDKClient() as client:
        await client.query(message_stream())

        async for message in client.receive_response():
            print(message)

        await client.query("Should we be concerned about these readings?")

        async for message in client.receive_response():
            print(message)

asyncio.run(main())
```

#### Example - Continuing a conversation

```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient, AssistantMessage, TextBlock

async def main():
    async with ClaudeSDKClient() as client:
        await client.query("What's the capital of France?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")

        await client.query("What's the population of that city?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")

asyncio.run(main())
```

## Classes

### `ClaudeSDKClient`

Maintains a conversation session across multiple exchanges.

```python
class ClaudeSDKClient:
    def __init__(
        self,
        options: ClaudeAgentOptions | None = None,
        transport: Transport | None = None
    )

    async def connect(
        self,
        prompt: str | AsyncIterable[dict[str, Any]] | None = None
    ) -> None

    async def query(
        self,
        prompt: str | AsyncIterable[dict[str, Any]],
        session_id: str = "default"
    ) -> None

    async def receive_messages(self) -> AsyncIterator[Message]
    async def receive_response(self) -> AsyncIterator[Message]
    async def interrupt(self) -> None
    async def set_permission_mode(self, mode: str) -> None
    async def set_model(self, model: str | None = None) -> None
    async def rewind_files(self, user_message_id: str) -> None
    async def get_server_info(self) -> dict[str, Any] | None
    async def disconnect(self) -> None
```

#### Methods

| Method | Description |
| :-- | :-- |
| `__init__(options, transport)` | Initialize the client with optional configuration and custom transport |
| `connect(prompt)` | Connect to Claude. If `prompt` is `None`, keeps the stream open |
| `query(prompt, session_id)` | Send a new request in streaming mode |
| `receive_messages()` | Receive all messages from Claude as an async iterator |
| `receive_response()` | Receive messages until and including a `ResultMessage` |
| `interrupt()` | Send interrupt signal (streaming mode only) |
| `set_permission_mode(mode)` | Change permission mode during the session |
| `set_model(model)` | Switch models during the session |
| `rewind_files(user_message_id)` | Restore files to their state at the specified user message |
| `get_server_info()` | Return server initialization metadata (commands, output styles, capabilities) |
| `disconnect()` | Disconnect from Claude |

Notes:
- `can_use_tool` requires streaming mode. If `options.can_use_tool` is set, `connect()` must use an `AsyncIterable` prompt and `permission_prompt_tool_name` must be unset.
- `rewind_files()` requires `enable_file_checkpointing=True` and `extra_args={"replay-user-messages": None}` to receive `UserMessage.uuid`.
- The client should be used within a single async runtime context from `connect()` to `disconnect()`.

#### Context Manager Support

```python
async with ClaudeSDKClient() as client:
    await client.query("Hello Claude")
    async for message in client.receive_response():
        print(message)
```

### `create_sdk_mcp_server()`

Create an in-process MCP server that runs within your Python application.

```python
def create_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None
) -> McpSdkServerConfig
```

#### Parameters

| Parameter | Type | Default | Description |
| :-- | :-- | :-- | :-- |
| `name` | `str` | - | Unique identifier for the server |
| `version` | `str` | `"1.0.0"` | Server version string |
| `tools` | `list[SdkMcpTool[Any]] | None` | `None` | List of tool functions created with `@tool` |

#### Returns

Returns an `McpSdkServerConfig` object that can be passed to `ClaudeAgentOptions.mcp_servers`.

#### Example

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions

@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {
        "content": [{
            "type": "text",
            "text": f"Sum: {args['a'] + args['b']}"
        }]
    }

@tool("multiply", "Multiply two numbers", {"a": float, "b": float})
async def multiply(args):
    return {
        "content": [{
            "type": "text",
            "text": f"Product: {args['a'] * args['b']}"
        }]
    }

calculator = create_sdk_mcp_server(
    name="calculator",
    version="2.0.0",
    tools=[add, multiply]
)

options = ClaudeAgentOptions(
    mcp_servers={"calc": calculator},
    allowed_tools=["mcp__calc__add", "mcp__calc__multiply"]
)
```

### `tool()`

Decorator for defining MCP tools with type safety.

```python
def tool(
    name: str,
    description: str,
    input_schema: type | dict[str, Any]
) -> Callable[[Callable[[Any], Awaitable[dict[str, Any]]]], SdkMcpTool[Any]]
```

#### Parameters

| Parameter | Type | Description |
| :-- | :-- | :-- |
| `name` | `str` | Unique identifier for the tool |
| `description` | `str` | Human-readable description of what the tool does |
| `input_schema` | `type | dict[str, Any]` | Schema defining the tool's input parameters |

#### Input Schema Options

1. Simple type mapping (recommended):

```python
{"text": str, "count": int, "enabled": bool}
```

2. TypedDict class (for structured types):

```python
class GreetInput(TypedDict):
    name: str
    title: str
```

3. JSON Schema format (for complex validation):

```python
{
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "count": {"type": "integer", "minimum": 0}
    },
    "required": ["text"]
}
```

#### Returns

A decorator function that wraps the tool implementation and returns an `SdkMcpTool` instance.

#### Example

```python
from claude_agent_sdk import tool
from typing import Any

@tool("greet", "Greet a user", {"name": str})
async def greet(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [{
            "type": "text",
            "text": f"Hello, {args['name']}!"
        }]
    }
```

## Choosing Between `query()` and `ClaudeSDKClient`

The SDK provides two ways to interact with Claude Code: a one-shot helper (`query()`) and a stateful client (`ClaudeSDKClient`).

### Quick Comparison

| Feature | `query()` | `ClaudeSDKClient` |
| :-- | :-- | :-- |
| Session | New session each call (unless `resume`/`continue_conversation` is used) | Reuses same session |
| Conversation | Unidirectional (send input, then receive output) | Multi-turn, interactive |
| Connection | Managed automatically | Manual control |
| Streaming input | Yes | Yes |
| Interrupts | No | Yes |
| Hooks | Yes (streaming input only) | Yes |
| SDK MCP tools | Yes (streaming input only) | Yes |
| Continue chat | New session by default | Maintains conversation |
| Use case | One-off tasks | Continuous conversations |

### When to Use `query()` (New Session Each Time)

Best for:
- One-off questions where you do not need history
- Independent tasks that do not require context
- Simple automation scripts
- Batch processing of prompts

### When to Use `ClaudeSDKClient` (Continuous Conversation)

Best for:
- Continuing conversations where context matters
- Follow-up questions that build on prior responses
- Interactive applications (chat UI, REPL)
- Response-driven logic and tool orchestration
- Interrupts and explicit session control

Note: If you set `can_use_tool` or need hooks/SDK MCP servers with `query()`, you must supply `prompt` as an `AsyncIterable` (streaming mode).

## Functions

### `query()`

Creates a new session for each interaction with Claude Code. Returns an async iterator that yields messages as they arrive.

```python
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None,
    transport: Transport | None = None
) -> AsyncIterator[Message]
```

#### Parameters

| Parameter | Type | Description |
| :-- | :-- | :-- |
| `prompt` | `str | AsyncIterable[dict[str, Any]]` | Input prompt as a string or async iterable for streaming mode |
| `options` | `ClaudeAgentOptions | None` | Optional configuration object (defaults to `ClaudeAgentOptions()` if None) |
| `transport` | `Transport | None` | Optional custom transport implementation |

#### Returns

Returns an `AsyncIterator[Message]` that yields messages from the conversation. If `include_partial_messages=True` in options, the iterator can also yield `StreamEvent` objects.

#### Streaming input format

Each streamed message should look like:

```python
{
    "type": "user",
    "message": {"role": "user", "content": "..."},
    "parent_tool_use_id": None,
    "session_id": "..."
}
```

#### Example - With options

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python developer",
        permission_mode="acceptEdits",
        cwd="/home/user/project"
    )

    async for message in query(
        prompt="Create a Python web server",
        options=options
    ):
        print(message)

asyncio.run(main())
```
