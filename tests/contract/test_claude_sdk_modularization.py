"""
Contract test for Claude SDK modularization.

This test enforces the "single import point" rule: claude_agent_sdk and
claude_code_sdk should only be imported in specific locations.

The purpose of this guardrail test is to prevent "just this one little import"
from creeping in later, which would undermine the modularization effort.

Allowed import locations:
- swarm/runtime/_claude_sdk/sdk_import.py - The single import point
- swarm/runtime/claude_sdk.py - The public façade that delegates to sdk_import.py

Run with: pytest tests/contract/test_claude_sdk_modularization.py -v
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "swarm" / "runtime"
INTERNAL_SDK_DIR = RUNTIME_DIR / "_claude_sdk"

# The patterns we're looking for
SDK_IMPORT_PATTERNS = [
    "import claude_agent_sdk",
    "import claude_code_sdk",
    "from claude_agent_sdk",
    "from claude_code_sdk",
]

# Files that are allowed to contain these imports
ALLOWED_FILES = {
    "swarm/runtime/_claude_sdk/sdk_import.py",
    "swarm/runtime/claude_sdk.py",
}


def _find_python_files(directory: Path) -> list[Path]:
    """Find all Python files in a directory recursively."""
    return list(directory.rglob("*.py"))


def _file_contains_sdk_import(file_path: Path) -> list[str]:
    """Check if a file contains any SDK import patterns.

    Returns:
        List of patterns found in the file.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        found_patterns = []
        for pattern in SDK_IMPORT_PATTERNS:
            if pattern in content:
                found_patterns.append(pattern)
        return found_patterns
    except Exception:
        # If we can't read the file, skip it
        return []


def test_sdk_imports_only_in_allowed_location():
    """Verify claude_agent_sdk and claude_code_sdk are only imported in allowed locations.

    This is a guardrail test to prevent SDK imports from spreading throughout
    the codebase. All SDK imports should go through sdk_import.py, with
    claude_sdk.py being the public façade that re-exports from the internal package.

    The test scans all Python files in swarm/runtime/ and swarm/runtime/_claude_sdk/
    and reports any violations found.
    """
    violations = []

    # Scan runtime directory
    runtime_files = _find_python_files(RUNTIME_DIR)

    for file_path in runtime_files:
        # Get relative path from repo root
        rel_path = str(file_path.relative_to(REPO_ROOT)).replace("\\", "/")

        # Skip test files
        if "tests/" in rel_path or "/test_" in rel_path or "_test.py" in rel_path:
            continue

        # Check if file contains SDK imports
        patterns_found = _file_contains_sdk_import(file_path)

        if patterns_found:
            # Check if this file is in the allowed list
            if rel_path not in ALLOWED_FILES:
                violations.append(
                    f"{rel_path}: Found SDK imports: {', '.join(patterns_found)}"
                )

    # If violations found, fail with a clear error message
    if violations:
        error_message = (
            "SDK imports found in unauthorized locations!\n\n"
            "claude_agent_sdk and claude_code_sdk should only be imported in:\n"
            "  - swarm/runtime/_claude_sdk/sdk_import.py (the single import point)\n"
            "  - swarm/runtime/claude_sdk.py (the public façade)\n\n"
            "Violations found:\n"
        )
        for violation in violations:
            error_message += f"  - {violation}\n"

        error_message += (
            "\n"
            "To fix this violation:\n"
            "1. Remove the direct SDK import from the violating file.\n"
            "2. Import from swarm.runtime.claude_sdk instead.\n"
            "3. If you need new SDK functionality, add it to the appropriate\n"
            "   module in swarm/runtime/_claude_sdk/ and re-export from claude_sdk.py."
        )

        pytest.fail(error_message)

    # If we get here, all imports are in the right place
    # Optionally, verify that the allowed files DO contain the imports
    sdk_import_file = INTERNAL_SDK_DIR / "sdk_import.py"
    claude_sdk_file = RUNTIME_DIR / "claude_sdk.py"

    # Check that sdk_import.py actually imports the SDK (or tries to)
    sdk_import_patterns = _file_contains_sdk_import(sdk_import_file)
    if not sdk_import_patterns:
        pytest.fail(
            f"Expected {sdk_import_file.relative_to(REPO_ROOT)} to contain SDK imports, "
            "but none were found. This may indicate the file structure has changed."
        )


def test_public_api_exports_stable():
    """Verify the public API exports from swarm.runtime.claude_sdk remain stable.

    This contract test ensures that all expected public API exports are present
    and accessible. It catches accidental API breaks during refactors.

    The test verifies:
    - All expected names from __all__ are present in the module
    - Functions and classes are callable (where applicable)
    - The ClaudeSDKClient alias works correctly

    Expected exports (from claude_sdk.py __all__):
    - SDK availability: SDK_AVAILABLE, check_sdk_available, get_sdk_module, get_sdk_module_name
    - Options builder: create_high_trust_options, create_options_from_plan
    - Query helpers: query_with_options, query_simple
    - Structured output schemas: HANDOFF_ENVELOPE_SCHEMA, ROUTING_SIGNAL_SCHEMA
    - Tool policy: ALL_STANDARD_TOOLS, compute_disallowed_tools, is_blocked_command, create_tool_policy_hook
    - Hooks: create_dangerous_command_hook, create_telemetry_hook
    - Session management: StepSessionClient
    - Compatibility: _dict_to_normalized_tool_call, ClaudeSDKClient, ClaudeCodeOptions
    - SDK shims: tool, create_sdk_mcp_server, Message types, hook types
    """
    import swarm.runtime.claude_sdk as claude_sdk

    # Expected exports based on __all__ in claude_sdk.py
    expected_exports = {
        # SDK availability
        "SDK_AVAILABLE",
        "check_sdk_available",
        "get_sdk_module",
        "get_sdk_module_name",
        "get_sdk_distribution",
        "get_sdk_version",
        "_sdk_module",
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
        "TelemetryData",
        # Compatibility
        "_dict_to_normalized_tool_call",
        "ClaudeSDKClient",  # Backward compatibility alias
        "ClaudeCodeOptions",  # Backward compatibility proxy
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
    }

    # Check that all expected exports exist
    missing_exports = []
    for name in expected_exports:
        if not hasattr(claude_sdk, name):
            missing_exports.append(name)

    if missing_exports:
        error_message = (
            "Public API exports are missing from swarm.runtime.claude_sdk!\n\n"
            "The following expected exports were not found:\n"
        )
        for name in missing_exports:
            error_message += f"  - {name}\n"

        error_message += (
            "\n"
            "This indicates the public API surface has changed.\n"
            "To fix this:\n"
            "1. If this is an intentional API change, update this test with the new expected exports.\n"
            "2. If this is accidental, ensure the export is properly re-exported from claude_sdk.py."
        )
        pytest.fail(error_message)

    # Verify that functions and classes are callable (where applicable)
    # This catches cases where a name exists but is not a proper export
    callable_exports = {
        "check_sdk_available",
        "get_sdk_module",
        "get_sdk_module_name",
        "get_sdk_distribution",
        "get_sdk_version",
        "create_high_trust_options",
        "create_options_from_plan",
        "query_with_options",
        "query_simple",
        "compute_disallowed_tools",
        "is_blocked_command",
        "create_tool_policy_hook",
        "create_dangerous_command_hook",
        "create_telemetry_hook",
        "StepSessionClient",
        "_dict_to_normalized_tool_call",
        "ClaudeSDKClient",
        "ClaudeCodeOptions",
        "TelemetryData",
        "MissingSdkFeatureError",
        "tool",
        "create_sdk_mcp_server",
    }

    non_callable = []
    for name in callable_exports:
        attr = getattr(claude_sdk, name)
        if not callable(attr):
            non_callable.append(name)

    if non_callable:
        error_message = (
            "The following expected exports are not callable:\n"
        )
        for name in non_callable:
            error_message += f"  - {name}\n"
        pytest.fail(error_message)

    # Verify ClaudeSDKClient alias works correctly
    # It should be an alias for StepSessionClient
    assert claude_sdk.ClaudeSDKClient is claude_sdk.StepSessionClient, (
        "ClaudeSDKClient should be an alias for StepSessionClient"
    )

    # Verify constants are present (not callable)
    constant_exports = {
        "SDK_AVAILABLE",
        "HANDOFF_ENVELOPE_SCHEMA",
        "ROUTING_SIGNAL_SCHEMA",
        "ALL_STANDARD_TOOLS",
    }

    for name in constant_exports:
        attr = getattr(claude_sdk, name)
        assert attr is not None, f"{name} should be present but is None"
