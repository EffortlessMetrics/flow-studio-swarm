import os
from unittest.mock import MagicMock
from swarm.runtime.backends import ClaudeHarnessBackend
from swarm.runtime.types import RunSpec

def test_claude_backend_build_command_security():
    """Test that build_command prevents shell injection via run_id."""
    backend = ClaudeHarnessBackend()

    # Malicious run_id that attempts shell injection
    malicious_run_id = "foo; rm -rf /"

    spec = RunSpec(
        flow_keys=["signal"],
        params={"run_id": malicious_run_id}
    )

    cmd, env_vars = backend._build_command("signal", spec)

    # Check command structure
    assert isinstance(cmd, list)
    assert cmd == ["make", "demo-signal"]

    # Check env vars
    assert isinstance(env_vars, dict)
    assert env_vars["RUN_ID"] == malicious_run_id

    # Ensure no shell injection in command
    cmd_str = " ".join(cmd)
    assert malicious_run_id not in cmd_str
    assert ";" not in cmd_str

def test_claude_backend_build_command_custom():
    """Test that custom command is handled correctly."""
    backend = ClaudeHarnessBackend()
    spec = RunSpec(
        flow_keys=["signal"],
        params={"command": "echo custom", "run_id": "test-id"}
    )

    cmd, env_vars = backend._build_command("signal", spec)

    assert cmd == ["echo", "custom"]
    assert env_vars["RUN_ID"] == "test-id"
