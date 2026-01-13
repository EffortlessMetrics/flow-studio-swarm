"""
Facade contract tests for the Claude SDK adapter.

These tests verify Flow Studio's adapter surface and runtime semantics without
depending on the upstream SDK being installed. Upstream drift checks live in
test_upstream_sdk_drift.py.
"""

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_DIR = REPO_ROOT / "docs" / "vendor" / "anthropic" / "agent-sdk" / "python"
TOOLS_MANIFEST = VENDOR_DIR / "TOOLS_MANIFEST.json"


def _load_vendor_tools() -> set[str]:
    """Load tool names from the vendored tools manifest."""
    if not TOOLS_MANIFEST.exists():
        pytest.skip("TOOLS_MANIFEST.json not present. Run make vendor-agent-sdk.")
    data = json.loads(TOOLS_MANIFEST.read_text(encoding="utf-8"))
    tool_names = set(data.get("tool_names", []))
    if not tool_names:
        pytest.skip("TOOLS_MANIFEST.json has no tool names.")
    return tool_names


# =============================================================================
# Adapter Availability Contract
# =============================================================================


class TestAdapterAvailability:
    """Verify adapter availability flags are consistent."""

    def test_sdk_availability_flag_consistent(self):
        """SDK_AVAILABLE matches check_sdk_available()."""
        from swarm.runtime.claude_sdk import SDK_AVAILABLE, check_sdk_available

        assert check_sdk_available() == SDK_AVAILABLE

    def test_official_package_preferred(self):
        """Verify we try claude_agent_sdk before claude_code_sdk."""
        from swarm.runtime import claude_sdk

        try:
            import claude_agent_sdk
            assert claude_sdk._sdk_module is claude_agent_sdk
        except ImportError:
            # Official package not installed; fallback is acceptable.
            pass


# =============================================================================
# P0: Facade Export Stability
# =============================================================================


class TestFacadeExports:
    """Verify the facade exports stable aliases and helpers."""

    def test_claude_sdk_client_alias(self):
        """ClaudeSDKClient remains an alias of StepSessionClient."""
        from swarm.runtime.claude_sdk import ClaudeSDKClient, StepSessionClient

        assert ClaudeSDKClient is StepSessionClient

    def test_claude_code_options_proxy(self):
        """ClaudeCodeOptions exists and maps to SDK options when available."""
        from swarm.runtime.claude_sdk import ClaudeCodeOptions, SDK_AVAILABLE, get_sdk_module

        assert ClaudeCodeOptions is not None
        if not SDK_AVAILABLE:
            pytest.skip("SDK not available; cannot validate options proxy")

        sdk = get_sdk_module()
        if hasattr(sdk, "ClaudeAgentOptions"):
            assert ClaudeCodeOptions.__class__ is sdk.ClaudeAgentOptions
        elif hasattr(sdk, "ClaudeCodeOptions"):
            assert ClaudeCodeOptions.__class__ is sdk.ClaudeCodeOptions
        else:
            pytest.skip("SDK does not expose an options class")

    def test_facade_all_exports(self):
        """Facade __all__ includes the stable public surface."""
        import swarm.runtime.claude_sdk as claude_sdk

        expected = {
            "ClaudeCodeOptions",
            "ClaudeSDKClient",
            "StepSessionClient",
            "query_with_options",
            "query_simple",
            "tool",
            "create_sdk_mcp_server",
            "HANDOFF_ENVELOPE_SCHEMA",
            "ROUTING_SIGNAL_SCHEMA",
        }
        missing = expected - set(claude_sdk.__all__)
        assert not missing, f"Facade __all__ missing: {missing}"


# =============================================================================
# P0: Import Boundary Contract
# =============================================================================


class TestImportBoundary:
    """Verify the SDK is only imported in the designated shim."""

    def test_single_sdk_import_point(self):
        """Only sdk_import.py may import claude_agent_sdk/claude_code_sdk."""
        runtime_dir = REPO_ROOT / "swarm" / "runtime"
        allowed = {runtime_dir / "_claude_sdk" / "sdk_import.py"}
        pattern = re.compile(r"^\s*(import|from)\s+claude_(agent|code)_sdk\b", re.MULTILINE)

        offenders = []
        for path in runtime_dir.rglob("*.py"):
            if path in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                offenders.append(str(path))

        assert not offenders, f"Direct SDK imports found outside sdk_import.py: {offenders}"


# =============================================================================
# P0: Tool Permission Semantics
# =============================================================================


class TestToolPermissionSemantics:
    """Verify tool permission handling."""

    def test_disallowed_tools_computation(self):
        """Verify compute_disallowed_tools produces correct complement."""
        from swarm.runtime.claude_sdk import (
            compute_disallowed_tools,
            ALL_STANDARD_TOOLS,
        )

        # Allow only Read and Write
        allowed = ["Read", "Write"]
        disallowed = compute_disallowed_tools(allowed)

        assert disallowed is not None
        assert "Read" not in disallowed
        assert "Write" not in disallowed
        assert "Bash" in disallowed
        assert "Edit" in disallowed

        # All disallowed + allowed should equal all standard tools
        all_tools = set(allowed) | set(disallowed)
        assert all_tools == ALL_STANDARD_TOOLS

    def test_no_restriction_returns_none(self):
        """Verify None allowed_tools returns None disallowed_tools."""
        from swarm.runtime.claude_sdk import compute_disallowed_tools

        result = compute_disallowed_tools(None)
        assert result is None

    def test_empty_allowed_disallows_all(self):
        """Verify empty allowed list disallows all standard tools."""
        from swarm.runtime.claude_sdk import (
            compute_disallowed_tools,
            ALL_STANDARD_TOOLS,
        )

        disallowed = compute_disallowed_tools([])
        assert disallowed is not None
        assert set(disallowed) == ALL_STANDARD_TOOLS


# =============================================================================
# P0: Structured Output Contract
# =============================================================================


class TestStructuredOutputContract:
    """Verify structured output extraction produces consistent results."""

    def test_fence_extraction_returns_data(self):
        """Fence parsing extracts JSON correctly."""
        from swarm.runtime.structured_output import extract_json_from_text

        response = '''
Here is the output:
```json
{"status": "VERIFIED", "summary": "Test completed"}
```
'''
        result, error = extract_json_from_text(response)

        assert result is not None
        assert error is None
        assert result["status"] == "VERIFIED"
        assert result["summary"] == "Test completed"

    def test_raw_json_extraction(self):
        """Raw JSON text is extracted correctly."""
        from swarm.runtime.structured_output import extract_json_from_text

        response = '{"status": "VERIFIED", "summary": "Test summary"}'
        result, error = extract_json_from_text(response)

        assert result is not None
        assert error is None
        assert result["status"] == "VERIFIED"

    def test_nested_json_in_text(self):
        """JSON embedded in surrounding text is extracted."""
        from swarm.runtime.structured_output import extract_json_from_text

        response = '''
Let me provide the output:
{"status": "UNVERIFIED", "concerns": ["issue1"]}
That concludes my analysis.
'''
        result, error = extract_json_from_text(response)

        assert result is not None
        assert result["status"] == "UNVERIFIED"

    def test_schema_validation_catches_missing_required(self):
        """Schema validation identifies missing required fields."""
        from swarm.runtime.structured_output import validate_against_schema

        schema = {
            "type": "object",
            "required": ["status", "summary"],
            "properties": {
                "status": {"type": "string"},
                "summary": {"type": "string"},
            }
        }

        # Missing 'summary' field
        data = {"status": "VERIFIED"}
        errors = validate_against_schema(data, schema)

        assert len(errors) > 0
        assert any("summary" in str(e) for e in errors)

    def test_schema_validation_catches_enum_violation(self):
        """Schema validation catches enum value violations."""
        from swarm.runtime.structured_output import validate_against_schema

        schema = {
            "type": "object",
            "required": ["status"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["VERIFIED", "UNVERIFIED", "BLOCKED"]
                },
            }
        }

        # Invalid enum value
        data = {"status": "INVALID_STATUS"}
        errors = validate_against_schema(data, schema)

        assert len(errors) > 0
        assert any("INVALID_STATUS" in str(e) or "enum" in str(e).lower() for e in errors)

    def test_schema_validation_passes_valid_data(self):
        """Valid data passes schema validation."""
        from swarm.runtime.structured_output import validate_against_schema

        schema = {
            "type": "object",
            "required": ["status", "summary"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["VERIFIED", "UNVERIFIED", "BLOCKED"]
                },
                "summary": {"type": "string"},
            }
        }

        data = {"status": "VERIFIED", "summary": "All tests passed"}
        errors = validate_against_schema(data, schema)

        assert len(errors) == 0


# =============================================================================
# P1: Session Semantics
# =============================================================================


class TestSessionSemantics:
    """Verify session capability declarations are explicit."""

    def test_capabilities_have_explicit_flags(self):
        """Verify TransportCapabilities has explicit capability flags."""
        from swarm.runtime.transports.port import TransportCapabilities

        caps = TransportCapabilities()

        # Should have explicit flags for key features
        # Session semantics are split: within-step and across-steps
        assert hasattr(caps, 'supports_hot_context_within_step')
        assert hasattr(caps, 'supports_context_across_steps')
        assert hasattr(caps, 'supports_output_format')
        assert hasattr(caps, 'supports_hooks')
        assert hasattr(caps, 'supports_interrupts')
        assert hasattr(caps, 'supports_sandbox')

    def test_claude_sdk_capabilities_correct(self):
        """Verify Claude SDK capabilities are set correctly."""
        from swarm.runtime.transports.port import CLAUDE_SDK_CAPABILITIES

        # Claude SDK supports hot context within a step (Work/Finalize/Route share session)
        assert CLAUDE_SDK_CAPABILITIES.supports_hot_context_within_step is True
        # But across steps, context is rehydrated from disk (session amnesia)
        assert CLAUDE_SDK_CAPABILITIES.supports_context_across_steps is False
        assert CLAUDE_SDK_CAPABILITIES.supports_output_format is True
        assert CLAUDE_SDK_CAPABILITIES.supports_hooks is True
        assert CLAUDE_SDK_CAPABILITIES.supports_native_tools is True

    def test_cli_capabilities_no_hot_context(self):
        """Verify CLI transports don't claim hot context support."""
        from swarm.runtime.transports.port import (
            CLAUDE_CLI_CAPABILITIES,
            GEMINI_CLI_CAPABILITIES,
        )

        # CLI calls are stateless - no hot context within step or across steps
        assert CLAUDE_CLI_CAPABILITIES.supports_hot_context_within_step is False
        assert GEMINI_CLI_CAPABILITIES.supports_hot_context_within_step is False
        assert CLAUDE_CLI_CAPABILITIES.supports_context_across_steps is False
        assert GEMINI_CLI_CAPABILITIES.supports_context_across_steps is False


# =============================================================================
# P1: Rewind/Checkpointing
# =============================================================================


class TestRewindCapability:
    """Verify rewind capability is explicitly documented as unsupported."""

    def test_rewind_explicitly_unsupported(self):
        """Verify supports_rewind is False with documentation."""
        from swarm.runtime.transports.port import CLAUDE_SDK_CAPABILITIES

        assert CLAUDE_SDK_CAPABILITIES.supports_rewind is False


# =============================================================================
# P1: Structured Output Fallback Strategies
# =============================================================================


class TestStructuredOutputFallback:
    """Verify fallback strategies are correctly declared."""

    def test_sdk_has_no_fallback_needed(self):
        """Claude SDK has native support, no fallback needed."""
        from swarm.runtime.transports.port import CLAUDE_SDK_CAPABILITIES

        assert CLAUDE_SDK_CAPABILITIES.structured_output_fallback == "none"

    def test_cli_uses_best_effort(self):
        """Claude CLI uses best-effort fence parsing."""
        from swarm.runtime.transports.port import CLAUDE_CLI_CAPABILITIES

        assert CLAUDE_CLI_CAPABILITIES.structured_output_fallback == "best-effort"

    def test_gemini_uses_microloop(self):
        """Gemini CLI uses microloop for validation."""
        from swarm.runtime.transports.port import GEMINI_CLI_CAPABILITIES

        assert GEMINI_CLI_CAPABILITIES.structured_output_fallback == "microloop"


# =============================================================================
# P1: Sandbox Capability
# =============================================================================


class TestSandboxCapability:
    """Verify sandbox enforcement is not claimed."""

    def test_sandbox_not_supported(self):
        """All transports should report sandbox enforcement as unsupported."""
        from swarm.runtime.transports.port import (
            CLAUDE_SDK_CAPABILITIES,
            CLAUDE_CLI_CAPABILITIES,
            GEMINI_CLI_CAPABILITIES,
            STUB_CAPABILITIES,
        )

        assert CLAUDE_SDK_CAPABILITIES.supports_sandbox is False
        assert CLAUDE_CLI_CAPABILITIES.supports_sandbox is False
        assert GEMINI_CLI_CAPABILITIES.supports_sandbox is False
        assert STUB_CAPABILITIES.supports_sandbox is False


# =============================================================================
# Integration: Gemini Multi-Tool Handling
# =============================================================================


class TestGeminiMultiToolHandling:
    """Verify Gemini engine handles interleaved tool calls correctly."""

    def test_engine_can_be_instantiated(self):
        """Verify the engine can be instantiated."""
        from swarm.runtime.engines.gemini import GeminiStepEngine

        engine = GeminiStepEngine(repo_root=Path("."))
        assert engine.engine_id == "gemini-step"

    def test_normalized_tool_call_from_gemini_events(self):
        """Verify NormalizedToolCall can be created from Gemini-style events."""
        from swarm.runtime.types.tool_call import NormalizedToolCall

        # Create a tool call like Gemini would produce
        tool_call = NormalizedToolCall(
            tool_name="Bash",
            tool_input={"command": "ls -la"},
            source="gemini-cli",
        )

        assert tool_call.tool_name == "Bash"
        assert tool_call.source == "gemini-cli"


# =============================================================================
# P0: Handoff Envelope Schema Contract
# =============================================================================


class TestHandoffEnvelopeSchema:
    """Verify handoff envelope schema is correctly defined."""

    def test_schema_has_required_fields(self):
        """Verify HANDOFF_ENVELOPE_SCHEMA requires expected fields."""
        from swarm.runtime.claude_sdk import HANDOFF_ENVELOPE_SCHEMA

        required = HANDOFF_ENVELOPE_SCHEMA.get("required", [])

        # These fields are required for valid handoffs
        assert "step_id" in required
        assert "flow_key" in required
        assert "run_id" in required
        assert "status" in required
        assert "summary" in required

    def test_status_enum_values(self):
        """Verify status field has correct enum values."""
        from swarm.runtime.claude_sdk import HANDOFF_ENVELOPE_SCHEMA

        props = HANDOFF_ENVELOPE_SCHEMA.get("properties", {})
        status_prop = props.get("status", {})
        enum_values = status_prop.get("enum", [])

        # Expected status values
        assert "VERIFIED" in enum_values
        assert "UNVERIFIED" in enum_values
        assert "BLOCKED" in enum_values


# =============================================================================
# P0: Routing Signal Schema Contract
# =============================================================================


class TestRoutingSignalSchema:
    """Verify routing signal schema is correctly defined."""

    def test_schema_has_required_fields(self):
        """Verify ROUTING_SIGNAL_SCHEMA requires expected fields."""
        from swarm.runtime.claude_sdk import ROUTING_SIGNAL_SCHEMA

        required = ROUTING_SIGNAL_SCHEMA.get("required", [])

        # These fields are required for valid routing signals
        assert "decision" in required
        assert "reason" in required
        assert "confidence" in required

    def test_decision_enum_values(self):
        """Verify decision field has correct enum values."""
        from swarm.runtime.claude_sdk import ROUTING_SIGNAL_SCHEMA

        props = ROUTING_SIGNAL_SCHEMA.get("properties", {})
        decision_prop = props.get("decision", {})
        enum_values = decision_prop.get("enum", [])

        # Expected decision values
        assert "advance" in enum_values
        assert "loop" in enum_values
        assert "terminate" in enum_values


# =============================================================================
# P1: Blocked Command Patterns
# =============================================================================


class TestBlockedCommandPatterns:
    """Verify dangerous command blocking works correctly."""

    def test_force_push_blocked(self):
        """Verify git push --force is blocked."""
        from swarm.runtime.claude_sdk import is_blocked_command

        is_blocked, pattern = is_blocked_command("git push origin main --force")
        assert is_blocked is True
        assert pattern is not None

    def test_rm_rf_root_blocked(self):
        """Verify rm -rf / is blocked."""
        from swarm.runtime.claude_sdk import is_blocked_command

        is_blocked, pattern = is_blocked_command("rm -rf /")
        assert is_blocked is True

    def test_safe_commands_allowed(self):
        """Verify safe commands are allowed."""
        from swarm.runtime.claude_sdk import is_blocked_command

        is_blocked, _ = is_blocked_command("git status")
        assert is_blocked is False

        is_blocked, _ = is_blocked_command("pytest tests/")
        assert is_blocked is False

        is_blocked, _ = is_blocked_command("ls -la")
        assert is_blocked is False


# =============================================================================
# P0: ALL_STANDARD_TOOLS Completeness
# =============================================================================


class TestToolListCompleteness:
    """Verify ALL_STANDARD_TOOLS stays in sync with known tools."""

    def test_all_standard_tools_covers_vendor_manifest(self):
        """Verify ALL_STANDARD_TOOLS covers vendored tool names."""
        from swarm.runtime.claude_sdk import ALL_STANDARD_TOOLS

        vendor_tools = _load_vendor_tools()
        missing = vendor_tools - ALL_STANDARD_TOOLS
        assert not missing, (
            f"ALL_STANDARD_TOOLS missing vendored tools: {missing}. "
            "Update ALL_STANDARD_TOOLS in swarm/runtime/_claude_sdk/constants.py."
        )

    def test_all_standard_tools_is_frozen(self):
        """Verify ALL_STANDARD_TOOLS is immutable (frozenset)."""
        from swarm.runtime.claude_sdk import ALL_STANDARD_TOOLS

        assert isinstance(ALL_STANDARD_TOOLS, frozenset), (
            "ALL_STANDARD_TOOLS should be a frozenset to prevent accidental mutation"
        )

    def test_all_standard_tools_contains_core_tools(self):
        """Verify ALL_STANDARD_TOOLS contains known core Claude Code tools."""
        from swarm.runtime.claude_sdk import ALL_STANDARD_TOOLS

        # These are documented Claude Code tools that should always be present
        core_tools = {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}

        missing = core_tools - ALL_STANDARD_TOOLS
        assert not missing, f"ALL_STANDARD_TOOLS missing core tools: {missing}"


# =============================================================================
# P1: Disallowed Tools Enforcement Documentation
# =============================================================================


class TestDisallowedToolsEnforcement:
    """Document enforcement behavior of disallowed_tools.

    IMPORTANT: The SDK's disallowed_tools parameter may behave differently
    than expected. This test class documents known limitations and verifies
    basic functionality of our adapter's tool restriction helpers.
    """

    def test_disallowed_tools_enforcement_documented(self):
        """Document that disallowed_tools enforcement depends on SDK behavior.

        IMPORTANT: The SDK may treat disallowed_tools as:
        - Hard block (raises error or refuses to execute)
        - Soft block (prompts user for confirmation)
        - Advisory only (logs warning but proceeds)

        This test documents this is a known limitation requiring SDK-level
        integration testing to verify actual enforcement behavior.

        Our adapter computes disallowed_tools correctly, but whether the SDK
        actually blocks those tools depends on SDK internals and may vary
        across SDK versions.

        See: docs/reference/SDK_CAPABILITIES.md for enforcement details
        See: platform.claude.com/cookbook/claude-agent-sdk-02
        """
        from swarm.runtime.claude_sdk import compute_disallowed_tools, ALL_STANDARD_TOOLS

        # Verify the function exists and works
        disallowed = compute_disallowed_tools(["Read"])
        assert disallowed is not None
        assert "Read" not in disallowed

        # Document the limitation in the assertion message
        assert len(disallowed) > 0, (
            "compute_disallowed_tools should return non-empty list when tools are restricted. "
            "NOTE: Actual enforcement of disallowed_tools depends on SDK behavior at runtime. "
            "The SDK may treat this as a hard block, soft block, or advisory only."
        )

    def test_disallowed_tools_complement_is_correct(self):
        """Verify disallowed_tools is the exact complement of allowed_tools."""
        from swarm.runtime.claude_sdk import compute_disallowed_tools, ALL_STANDARD_TOOLS

        allowed = ["Read", "Write", "Glob"]
        disallowed = compute_disallowed_tools(allowed)

        # Disallowed should contain everything except allowed
        expected_disallowed = ALL_STANDARD_TOOLS - set(allowed)
        assert set(disallowed) == expected_disallowed, (
            f"Disallowed tools should be complement of allowed. "
            f"Expected: {expected_disallowed}, Got: {set(disallowed)}"
        )

    def test_all_tools_allowed_returns_none(self):
        """Verify None allowed_tools means no restriction (returns None)."""
        from swarm.runtime.claude_sdk import compute_disallowed_tools

        result = compute_disallowed_tools(None)
        assert result is None, (
            "When allowed_tools is None (all tools allowed), "
            "disallowed_tools should also be None (no restrictions)"
        )


# =============================================================================
# P1: Tool Call Normalization
# =============================================================================


class TestToolCallNormalization:
    """Verify tool calls are normalized consistently across sources."""

    def test_normalized_tool_call_fields(self):
        """Verify NormalizedToolCall has expected fields."""
        from swarm.runtime.types.tool_call import NormalizedToolCall

        tool_call = NormalizedToolCall(
            tool_name="Read",
            tool_input={"file_path": "/path/to/file"},
        )

        assert tool_call.tool_name == "Read"
        assert tool_call.tool_input == {"file_path": "/path/to/file"}
        assert hasattr(tool_call, 'tool_output')
        assert hasattr(tool_call, 'success')
        assert hasattr(tool_call, 'duration_ms')
        assert hasattr(tool_call, 'blocked')
        assert hasattr(tool_call, 'source')

    def test_dict_to_normalized_conversion(self):
        """Verify legacy dict format converts to NormalizedToolCall."""
        from swarm.runtime.claude_sdk import _dict_to_normalized_tool_call

        legacy_dict = {
            "tool": "Bash",
            "input": {"command": "ls -la"},
            "output": "total 42...",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        normalized = _dict_to_normalized_tool_call(legacy_dict)

        assert normalized.tool_name == "Bash"
        assert normalized.tool_input == {"command": "ls -la"}
        assert normalized.tool_output == "total 42..."
