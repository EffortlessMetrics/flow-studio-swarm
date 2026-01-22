"""Tests for GeminiCliBackend security and _build_command behavior.

These tests verify that the backend properly handles run_id parameters
without allowing command injection via shell metacharacters.
"""

from __future__ import annotations

import pytest
from swarm.runtime.backends import GeminiCliBackend
from swarm.runtime.types import RunSpec


class TestGeminiCliBackendSecurityInjection:
    """Security tests verifying command injection is prevented.

    These tests verify that malicious run_id values containing shell
    metacharacters are safely passed via environment variables and
    cannot alter the executed command structure.
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
    def test_build_command_injection_prevented_stub_mode(
        self, malicious_run_id: str, description: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that malicious run_id cannot inject shell commands in stub mode.

        In stub mode:
        1. Command should be python3 (safe execution)
        2. Malicious run_id should be in environment, not in python script
        """
        monkeypatch.setenv("SWARM_GEMINI_STUB", "1")
        backend = GeminiCliBackend()
        spec = RunSpec(
            flow_keys=["signal"],
            backend="gemini-cli",
            initiator="test",
        )

        cmd, env = backend._build_command("signal", malicious_run_id, spec)

        # Command must be safe python execution
        assert cmd[0] == "python3"
        assert cmd[1] == "-c"

        # The python script should NOT contain the malicious run_id directly
        # It should read it from environment
        script = cmd[2]
        assert malicious_run_id not in script
        assert "os.environ.get" in script

        # Malicious run_id is safely contained in environment
        assert "RUN_ID" in env
        assert env["RUN_ID"] == malicious_run_id

    @pytest.mark.parametrize(
        "malicious_run_id,description",
        [
            ("test; echo INJECTED", "semicolon command separator"),
            ("test && rm -rf /", "AND operator"),
        ],
    )
    def test_build_command_injection_prevented_real_mode(
        self, malicious_run_id: str, description: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that malicious run_id cannot inject shell commands in real mode.

        In real mode:
        1. Command should be gemini
        2. Malicious run_id is in env
        3. Malicious run_id IS in prompt (as data), but shell=False prevents execution
        """
        monkeypatch.setenv("SWARM_GEMINI_STUB", "0")
        backend = GeminiCliBackend()
        # Mock cli availability
        backend.cli_available = True

        spec = RunSpec(
            flow_keys=["signal"],
            backend="gemini-cli",
            initiator="test",
        )

        cmd, env = backend._build_command("signal", malicious_run_id, spec)

        # Command must be gemini
        assert "gemini" in cmd[0]

        # Malicious run_id is in environment
        assert env["RUN_ID"] == malicious_run_id

        # Check command structure
        assert "--output-format" in cmd
        assert "stream-json" in cmd

        # It is safe for run_id to be in prompt argument because shell=False
        # But let's verify it didn't break out of the prompt argument
        # (Since cmd is a list, this is guaranteed by subprocess logic,
        # but we check cmd structure here)

        prompt_idx = cmd.index("--prompt")
        prompt_arg = cmd[prompt_idx + 1]

        assert malicious_run_id in prompt_arg
        # Ensure it's contained within the prompt string
        assert f"Run ID: {malicious_run_id}" in prompt_arg

    def test_env_isolation_from_command_stub_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify environment dict is separate from command list in stub mode."""
        monkeypatch.setenv("SWARM_GEMINI_STUB", "1")
        backend = GeminiCliBackend()
        malicious = "$(rm -rf /)"
        spec = RunSpec(
            flow_keys=["build"],
            backend="gemini-cli",
            initiator="test",
        )

        cmd, env = backend._build_command("build", malicious, spec)

        # The malicious string must not appear in any command argument
        cmd_str = " ".join(cmd)
        assert malicious not in cmd_str
        # We can't check for "rm" simply because "swarm" contains "rm"
        assert "rm -rf" not in cmd_str

        # But it must be in the environment
        assert env.get("RUN_ID") == malicious

    def test_build_stub_command_python_injection_prevented(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that malicious flow_key cannot inject python code in stub mode."""
        monkeypatch.setenv("SWARM_GEMINI_STUB", "1")
        backend = GeminiCliBackend()

        # Malicious flow_key that tries to close the string literal and execute code
        # if code was: print('{events_str}')
        # injection: ' ); import os; os.system("echo PWNED"); print( '
        malicious_flow_key = "test'); import os; os.system('echo PWNED'); print('"

        spec = RunSpec(
            flow_keys=[malicious_flow_key],
            backend="gemini-cli",
            initiator="test",
        )

        # We call _build_command which calls _build_stub_command
        cmd, env = backend._build_command(malicious_flow_key, "run-123", spec)

        # Check that the malicious string is NOT in the python script (cmd[2])
        # The script is fixed: "import os, sys; print(sys.argv[1]); ..."
        script = cmd[2]
        assert "echo PWNED" not in script

        # But verify structure contains safe argument reading
        assert "sys.argv[1]" in script

        # The malicious string SHOULD be in the argument (cmd[3])
        # because it is passed as data
        events_arg = cmd[3]
        assert "echo PWNED" in events_arg
