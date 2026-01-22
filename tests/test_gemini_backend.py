"""Tests for GeminiCliBackend.

These tests verify the Gemini CLI backend works correctly with both
stub mode (for CI) and real CLI mode (when gemini is installed).
"""

from __future__ import annotations

import shutil

import pytest
from swarm.runtime.backends import GeminiCliBackend
from swarm.runtime.types import RunSpec


class TestGeminiCliBackendStubMode:
    """Tests for GeminiCliBackend in stub mode (CI-safe)."""

    def test_uses_stub_when_env_flag_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Backend uses stub when SWARM_GEMINI_STUB=1."""
        monkeypatch.setenv("SWARM_GEMINI_STUB", "1")
        backend = GeminiCliBackend()

        spec = RunSpec(
            flow_keys=["signal"],
            profile_id=None,
            backend="gemini-cli",
            initiator="test",
        )

        cmd = backend._build_command("signal", "test-run-001", spec)

        # _build_command returns List[str] for safe shell=False execution
        # Stub command uses echo, not real gemini binary
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        assert "echo -e" in cmd_str
        # Ensure we're not invoking the real gemini CLI (space-bounded to avoid
        # matching "gemini-cli" in the JSON stub output)
        assert " gemini " not in cmd_str

    def test_uses_stub_when_cli_not_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Backend uses stub when gemini CLI is not on PATH."""
        monkeypatch.setenv("SWARM_GEMINI_STUB", "0")
        monkeypatch.setenv("SWARM_GEMINI_CLI", "nonexistent-gemini-cli-xyz")

        backend = GeminiCliBackend()

        # Should detect CLI is not available
        assert backend.cli_available is False

        spec = RunSpec(
            flow_keys=["build"],
            profile_id=None,
            backend="gemini-cli",
            initiator="test",
        )

        cmd = backend._build_command("build", "test-run-002", spec)

        # _build_command returns List[str] for safe shell=False execution
        # Falls back to stub
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        assert "echo -e" in cmd_str

    def test_stub_command_includes_flow_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stub command includes the flow key in output."""
        monkeypatch.setenv("SWARM_GEMINI_STUB", "1")
        backend = GeminiCliBackend()

        spec = RunSpec(
            flow_keys=["gate"],
            profile_id=None,
            backend="gemini-cli",
            initiator="test",
        )

        cmd = backend._build_command("gate", "test-run-003", spec)

        # _build_command returns List[str] for safe shell=False execution
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        assert "gate" in cmd_str

    def test_custom_command_override_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Backend ignores custom command in spec params for security."""
        monkeypatch.setenv("SWARM_GEMINI_STUB", "1")
        backend = GeminiCliBackend()

        spec = RunSpec(
            flow_keys=["signal"],
            profile_id=None,
            backend="gemini-cli",
            initiator="test",
            params={"command": "echo 'custom command'"},
        )

        cmd = backend._build_command("signal", "test-run-004", spec)

        # Should NOT use custom command, but fallback to stub or real command
        # Since STUB=1, it should use the stub command
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        assert "echo -e" in cmd_str
        assert "custom command" not in cmd_str


class TestGeminiCliBackendCapabilities:
    """Tests for backend capabilities reporting."""

    def test_capabilities_id(self) -> None:
        """Backend reports correct ID."""
        backend = GeminiCliBackend()
        caps = backend.capabilities()
        assert caps.id == "gemini-cli"

    def test_capabilities_label(self) -> None:
        """Backend reports human-readable label."""
        backend = GeminiCliBackend()
        caps = backend.capabilities()
        assert caps.label == "Gemini CLI"

    def test_capabilities_streaming(self) -> None:
        """Backend supports streaming."""
        backend = GeminiCliBackend()
        caps = backend.capabilities()
        assert caps.supports_streaming is True

    def test_capabilities_events(self) -> None:
        """Backend supports events."""
        backend = GeminiCliBackend()
        caps = backend.capabilities()
        assert caps.supports_events is True

    def test_capabilities_cancel(self) -> None:
        """Backend supports cancellation."""
        backend = GeminiCliBackend()
        caps = backend.capabilities()
        assert caps.supports_cancel is True


class TestGeminiEventMapping:
    """Tests for Gemini event to RunEvent mapping."""

    def test_maps_init_event(self) -> None:
        """Maps init event correctly."""
        backend = GeminiCliBackend()

        gemini_event = {
            "type": "init",
            "backend": "gemini-cli",
            "flow": "signal",
        }

        run_event = backend._map_gemini_event("run-123", "signal", gemini_event)

        assert run_event is not None
        assert run_event.kind == "backend_init"
        assert run_event.payload["backend"] == "gemini-cli"

    def test_maps_message_event(self) -> None:
        """Maps message event with role."""
        backend = GeminiCliBackend()

        gemini_event = {
            "type": "message",
            "role": "assistant",
            "content": "Processing flow...",
        }

        run_event = backend._map_gemini_event("run-123", "build", gemini_event)

        assert run_event is not None
        assert run_event.kind == "assistant_message"

    def test_maps_tool_use_event(self) -> None:
        """Maps tool_use event."""
        backend = GeminiCliBackend()

        gemini_event = {
            "type": "tool_use",
            "tool": "read",
            "input": {"path": "src/main.rs"},
        }

        run_event = backend._map_gemini_event("run-123", "build", gemini_event)

        assert run_event is not None
        assert run_event.kind == "tool_start"
        assert run_event.payload["tool"] == "read"

    def test_maps_tool_result_event(self) -> None:
        """Maps tool_result event."""
        backend = GeminiCliBackend()

        gemini_event = {
            "type": "tool_result",
            "tool": "read",
            "success": True,
            "output": "file contents...",
        }

        run_event = backend._map_gemini_event("run-123", "build", gemini_event)

        assert run_event is not None
        assert run_event.kind == "tool_end"
        assert run_event.payload["success"] is True

    def test_maps_error_event(self) -> None:
        """Maps error event."""
        backend = GeminiCliBackend()

        gemini_event = {
            "type": "error",
            "error": "Something went wrong",
        }

        run_event = backend._map_gemini_event("run-123", "gate", gemini_event)

        assert run_event is not None
        assert run_event.kind == "error"
        assert "error" in run_event.payload

    def test_maps_result_event(self) -> None:
        """Maps result (completion) event."""
        backend = GeminiCliBackend()

        gemini_event = {
            "type": "result",
            "flow": "deploy",
            "status": "complete",
        }

        run_event = backend._map_gemini_event("run-123", "deploy", gemini_event)

        assert run_event is not None
        assert run_event.kind == "step_complete"
        assert run_event.payload["status"] == "complete"

    def test_maps_legacy_text_event(self) -> None:
        """Maps legacy text event from stub."""
        backend = GeminiCliBackend()

        gemini_event = {
            "type": "text",
            "message": "Processing...",
        }

        run_event = backend._map_gemini_event("run-123", "signal", gemini_event)

        assert run_event is not None
        assert run_event.kind == "log"


@pytest.mark.skipif(
    shutil.which("gemini") is None,
    reason="Gemini CLI not installed"
)
class TestGeminiCliBackendRealCli:
    """Tests that require the real gemini CLI to be installed.

    These tests are skipped in CI where gemini is not available.
    """

    def test_builds_real_command_when_stub_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Backend builds real gemini command when stub mode disabled."""
        monkeypatch.setenv("SWARM_GEMINI_STUB", "0")

        backend = GeminiCliBackend()

        # Should detect CLI is available
        assert backend.cli_available is True

        spec = RunSpec(
            flow_keys=["signal"],
            profile_id=None,
            backend="gemini-cli",
            initiator="test",
        )

        cmd = backend._build_command("signal", "test-run-123", spec)

        # Real command uses gemini CLI
        assert "gemini" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd

    def test_prompt_includes_flow_context(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Real CLI prompt includes flow and run context."""
        monkeypatch.setenv("SWARM_GEMINI_STUB", "0")

        backend = GeminiCliBackend()

        spec = RunSpec(
            flow_keys=["build"],
            profile_id=None,
            backend="gemini-cli",
            initiator="test",
            params={"title": "Test Build"},
        )

        prompt = backend._build_prompt("build", "test-run-456", spec)

        assert "build" in prompt.lower()
        assert "test-run-456" in prompt
