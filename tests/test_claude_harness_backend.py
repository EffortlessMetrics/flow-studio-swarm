
import unittest
from swarm.runtime.backends import ClaudeHarnessBackend
from swarm.runtime.types import RunSpec

class TestClaudeHarnessBackend(unittest.TestCase):
    def test_build_command_normal(self):
        backend = ClaudeHarnessBackend()
        spec = RunSpec(
            flow_keys=["signal"],
            backend="claude-harness",
            params={"run_id": "test-run"}
        )
        cmd, env = backend._build_command("signal", spec)

        self.assertEqual(cmd, ["make", "demo-signal"])
        self.assertEqual(env["RUN_ID"], "test-run")

    def test_build_command_custom(self):
        backend = ClaudeHarnessBackend()
        spec = RunSpec(
            flow_keys=["signal"],
            backend="claude-harness",
            params={"command": "echo hello", "run_id": "test-run"}
        )
        cmd, env = backend._build_command("signal", spec)

        self.assertEqual(cmd, ["echo", "hello"])
        self.assertEqual(env["RUN_ID"], "test-run")

    def test_build_command_fallback(self):
        backend = ClaudeHarnessBackend()
        spec = RunSpec(
            flow_keys=["unknown-flow"],
            backend="claude-harness",
            params={"run_id": "test-run"}
        )
        cmd, env = backend._build_command("unknown-flow", spec)

        self.assertEqual(cmd, ["echo", "Flow unknown-flow would run here"])
        self.assertEqual(env["RUN_ID"], "test-run")

    def test_build_command_security_injection(self):
        """Verify that run_id cannot inject shell commands."""
        backend = ClaudeHarnessBackend()
        malicious_run_id = "test; echo 'INJECTED'"
        spec = RunSpec(
            flow_keys=["signal"],
            backend="claude-harness",
            params={"run_id": malicious_run_id}
        )

        cmd, env = backend._build_command("signal", spec)

        # Check that command does NOT contain shell execution of the ID
        self.assertNotEqual(cmd[0], "sh")
        self.assertEqual(cmd, ['make', 'demo-signal'])

        # Check that ID is safely in environment
        self.assertIn("RUN_ID", env)
        self.assertEqual(env["RUN_ID"], malicious_run_id)

if __name__ == "__main__":
    unittest.main()
