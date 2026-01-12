"""
Contract tests for Claude SDK integration.

These tests verify that the Flow Studio SDK adapter correctly implements
the contract with the upstream Claude SDK package. They catch misalignments
between our adapter assumptions and actual SDK behavior.

Run with: pytest tests/contract/ -v
Skip if SDK not installed: pytest tests/contract/ -v (auto-skips)
"""

import pytest
from typing import Dict, Any, List, Optional


# =============================================================================
# Fixtures and Helpers
# =============================================================================

@pytest.fixture
def sdk_available():
    """Check if SDK is available, skip tests if not."""
    try:
        from swarm.runtime.claude_sdk import SDK_AVAILABLE
        if not SDK_AVAILABLE:
            pytest.skip("Claude SDK not installed")
        return True
    except ImportError:
        pytest.skip("swarm.runtime.claude_sdk not importable")


# =============================================================================
# P0: SDK Import Contract
# =============================================================================

class TestSDKImport:
    """Verify SDK import and package availability."""

    def test_sdk_import_succeeds(self, sdk_available):
        """Confirm SDK can be imported via our adapter."""
        from swarm.runtime.claude_sdk import get_sdk_module
        sdk = get_sdk_module()
        assert sdk is not None

    def test_sdk_has_expected_exports(self, sdk_available):
        """Verify SDK exports the types we depend on."""
        from swarm.runtime.claude_sdk import get_sdk_module
        sdk = get_sdk_module()

        # These are the SDK exports we actually use
        expected_attrs = [
            'ClaudeCodeOptions',  # Options builder
            'query',              # Stateless query function
        ]

        for attr in expected_attrs:
            assert hasattr(sdk, attr), f"SDK missing expected export: {attr}"

    def test_official_package_preferred(self):
        """Verify we try claude_agent_sdk before claude_code_sdk."""
        # This test inspects the import logic indirectly
        from swarm.runtime import claude_sdk

        # If claude_agent_sdk is installed, that's what should be loaded
        try:
            import claude_agent_sdk
            # Official package available - should be what we're using
            assert claude_sdk._sdk_module is claude_agent_sdk
        except ImportError:
            # Official not available - fallback is acceptable
            pass


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
# Integration: Gemini Multi-Tool Handling
# =============================================================================

class TestGeminiMultiToolHandling:
    """Verify Gemini engine handles interleaved tool calls correctly."""

    def test_engine_can_be_instantiated(self):
        """Verify the engine can be instantiated."""
        from swarm.runtime.engines.gemini import GeminiStepEngine
        from pathlib import Path

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
