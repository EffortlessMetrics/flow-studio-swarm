"""
Upstream SDK drift checks.

These tests compare the installed SDK to vendored artifacts. They skip when
the SDK is not installed and should fail with an actionable message when drift
is detected.
"""

import inspect

import pytest

from swarm.tools import vendor_agent_sdk


@pytest.fixture
def sdk_available():
    """Skip if SDK is not installed, otherwise return the module."""
    _, _, mod = vendor_agent_sdk.try_import_sdk()
    if mod is None:
        if vendor_agent_sdk.should_require_sdk():
            pytest.fail("Claude SDK not installed. Run: uv sync --extra dev")
        pytest.skip("Claude SDK not installed")
    return mod


def test_vendor_artifacts_match_installed_sdk(sdk_available):
    """Vendored artifacts should match the installed SDK."""
    status = vendor_agent_sdk.cmd_check()
    if status != 0:
        pytest.fail("Vendored SDK artifacts are stale. Run: make vendor-agent-sdk")


def test_sdk_import_succeeds(sdk_available):
    """Confirm SDK can be imported via our adapter."""
    from swarm.runtime.claude_sdk import get_sdk_module

    sdk = get_sdk_module()
    assert sdk is not None


def test_sdk_has_required_symbols(sdk_available):
    """Verify SDK exports the symbols the adapter depends on."""
    from swarm.runtime.claude_sdk import get_sdk_module

    sdk = get_sdk_module()
    assert hasattr(sdk, "query"), "SDK missing required export: query"
    assert (
        hasattr(sdk, "ClaudeAgentOptions") or hasattr(sdk, "ClaudeCodeOptions")
    ), "SDK missing options class (ClaudeAgentOptions/ClaudeCodeOptions)"


def test_sdk_options_accept_disallowed_tools(sdk_available):
    """Verify SDK options class accepts disallowed_tools parameter if exposed."""
    from swarm.runtime.claude_sdk import get_sdk_module

    sdk = get_sdk_module()
    options_cls = None
    if hasattr(sdk, "ClaudeAgentOptions"):
        options_cls = sdk.ClaudeAgentOptions
    elif hasattr(sdk, "ClaudeCodeOptions"):
        options_cls = sdk.ClaudeCodeOptions
    else:
        pytest.skip("SDK does not expose an options class")

    try:
        sig = inspect.signature(options_cls)
        params = list(sig.parameters.keys())
    except (ValueError, TypeError):
        pytest.skip("Could not inspect SDK options class signature")

    if "disallowed_tools" not in params:
        pytest.skip("SDK options class does not accept disallowed_tools")

    try:
        options = options_cls(
            cwd=".",
            permission_mode="bypassPermissions",
            disallowed_tools=["Bash"],
        )
        assert options is not None
    except Exception as e:
        pytest.fail(
            f"SDK accepts disallowed_tools but options creation failed: {e}"
        )


def test_all_standard_tools_covers_sdk_tools(sdk_available):
    """Verify ALL_STANDARD_TOOLS covers SDK tool list if exposed."""
    from swarm.runtime.claude_sdk import ALL_STANDARD_TOOLS, get_sdk_module

    sdk = get_sdk_module()

    sdk_tools = None
    for attr in ["TOOLS", "ALL_TOOLS", "STANDARD_TOOLS", "get_tools", "available_tools"]:
        if hasattr(sdk, attr):
            value = getattr(sdk, attr)
            if callable(value):
                try:
                    sdk_tools = set(value())
                except Exception:
                    continue
            elif isinstance(value, (list, set, tuple, frozenset)):
                sdk_tools = set(value)
            break

    if sdk_tools is None:
        pytest.skip(
            "SDK does not expose tool list via known attributes "
            "(TOOLS, ALL_TOOLS, STANDARD_TOOLS, get_tools, available_tools)."
        )

    missing = sdk_tools - ALL_STANDARD_TOOLS
    assert not missing, (
        f"ALL_STANDARD_TOOLS missing SDK tools: {missing}. "
        "Update ALL_STANDARD_TOOLS in swarm/runtime/_claude_sdk/constants.py."
    )
