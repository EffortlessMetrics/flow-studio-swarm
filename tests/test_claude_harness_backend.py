"""Tests for ClaudeHarnessBackend security and _build_command behavior.

These tests verify that the backend properly handles run_id parameters
without allowing command injection via shell metacharacters.
"""

from __future__ import annotations

import pytest
from swarm.runtime.backends import ClaudeHarnessBackend
from swarm.runtime.types import RunSpec


class TestClaudeHarnessBackendBuildCommand:
    """Tests for ClaudeHarnessBackend._build_command method."""

    def test_build_command_normal(self) -> None:
        """Normal run_id is passed via environment, not shell."""
        backend = ClaudeHarnessBackend()
        spec = RunSpec(
            flow_keys=["signal"],
            backend="claude-harness",
            params={"run_id": "test-run-001"},
        )
        cmd, env = backend._build_command("signal", spec)

        assert cmd == ["make", "demo-signal"]
        assert env["RUN_ID"] == "test-run-001"

    def test_build_command_no_run_id(self) -> None:
        """When run_id is absent, env dict should not contain RUN_ID."""
        backend = ClaudeHarnessBackend()
        spec = RunSpec(
            flow_keys=["signal"],
            backend="claude-harness",
            params={},
        )
        cmd, env = backend._build_command("signal", spec)

        assert cmd == ["make", "demo-signal"]
        assert "RUN_ID" not in env

    def test_build_command_custom_ignored(self) -> None:
        """Custom command in params should be ignored for security."""
        backend = ClaudeHarnessBackend()
        spec = RunSpec(
            flow_keys=["signal"],
            backend="claude-harness",
            params={"command": "echo hello", "run_id": "test-run"},
        )
        cmd, env = backend._build_command("signal", spec)

        # Should fall back to standard signal command
        assert cmd == ["make", "demo-signal"]
        assert env["RUN_ID"] == "test-run"

    def test_build_command_fallback(self) -> None:
        """Unknown flow key returns fallback echo, run_id in env."""
        backend = ClaudeHarnessBackend()
        spec = RunSpec(
            flow_keys=["unknown-flow"],
            backend="claude-harness",
            params={"run_id": "test-run"},
        )
        cmd, env = backend._build_command("unknown-flow", spec)

        assert cmd == ["echo", "Flow unknown-flow would run here"]
        assert env["RUN_ID"] == "test-run"


class TestClaudeHarnessBackendSecurityInjection:
    """Security tests verifying command injection is prevented.

    These tests verify that malicious run_id values containing shell
    metacharacters are safely passed via environment variables and
    cannot alter the executed command.
    """

    @pytest.mark.parametrize(
        "malicious_run_id,description",
        [
            ("test; echo INJECTED", "semicolon command separator"),
            ("test && rm -rf /", "AND operator"),
            ("test || cat /etc/passwd", "OR operator"),
            ("test`id`", "backtick command substitution"),
            ("test$(whoami)", "dollar-paren command substitution"),
            ("test\necho INJECTED", "newline injection"),
            ("test|cat /etc/passwd", "pipe injection"),
            ("test > /tmp/pwned", "output redirection"),
            ("test < /etc/passwd", "input redirection"),
            ("$(cat /etc/passwd)", "pure command substitution"),
            ("'; DROP TABLE users; --", "SQL-style injection attempt"),
            ('test"$(id)"', "quoted command substitution"),
        ],
    )
    def test_build_command_injection_prevented(
        self, malicious_run_id: str, description: str
    ) -> None:
        """Verify that malicious run_id cannot inject shell commands.

        The fix ensures:
        1. Command list never starts with 'sh' (no shell wrapper)
        2. Command is always the expected make target
        3. Malicious run_id is safely isolated in environment
        """
        backend = ClaudeHarnessBackend()
        spec = RunSpec(
            flow_keys=["signal"],
            backend="claude-harness",
            params={"run_id": malicious_run_id},
        )

        cmd, env = backend._build_command("signal", spec)

        # Command must NOT use shell wrapper
        assert cmd[0] != "sh", f"Shell wrapper detected for: {description}"

        # Command must be the expected make target
        assert cmd == ["make", "demo-signal"], f"Unexpected command for: {description}"

        # Malicious run_id is safely contained in environment
        assert "RUN_ID" in env
        assert env["RUN_ID"] == malicious_run_id

    def test_env_isolation_from_command(self) -> None:
        """Verify environment dict is separate from command list.

        This ensures the malicious value cannot leak into the command
        arguments through any string concatenation.
        """
        backend = ClaudeHarnessBackend()
        malicious = "$(rm -rf /)"
        spec = RunSpec(
            flow_keys=["build"],
            backend="claude-harness",
            params={"run_id": malicious},
        )

        cmd, env = backend._build_command("build", spec)

        # The malicious string must not appear in any command argument
        cmd_str = " ".join(cmd)
        assert malicious not in cmd_str
        assert "rm" not in cmd_str

        # But it must be in the environment
        assert env.get("RUN_ID") == malicious
