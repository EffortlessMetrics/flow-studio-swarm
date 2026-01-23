"""
Tests for selftest-core CLI.

Verifies that the selftest-core package CLI works correctly when invoked
as a subprocess. This ensures the package can be used as a standalone tool.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SELFTEST_CORE_DIR = Path(__file__).parent.parent / "packages" / "selftest-core"


class TestSelftestCoreCLI:
    """Test selftest-core CLI commands."""

    def test_help_flag(self):
        """selftest --help should exit 0 and show usage."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        assert result.returncode == 0
        assert "selftest" in result.stdout.lower()
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_version_flag(self):
        """selftest --version should exit 0 and show version."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "--version"],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        assert result.returncode == 0
        assert "selftest-core" in result.stdout or "0." in result.stdout

    def test_doctor_command(self):
        """selftest doctor should run diagnostics."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "doctor"],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        # Doctor returns 0 for HEALTHY, 1 for issues
        assert result.returncode in (0, 1)
        # Should produce some output
        assert len(result.stdout) > 0 or len(result.stderr) > 0

    def test_doctor_json_output(self):
        """selftest doctor --json should output valid JSON."""
        import json

        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "doctor", "--json"],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        assert result.returncode in (0, 1)
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "summary" in data
        assert data["summary"] in ("HEALTHY", "HARNESS_ISSUE", "SERVICE_ISSUE")

    def test_plan_command_no_config(self):
        """selftest plan without config should show error."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "plan"],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        # Should fail gracefully (exit 2 for config error or 0 with message)
        # When no config, it returns error or empty plan
        assert result.returncode in (0, 2)

    def test_run_command_no_config(self):
        """selftest run without config should show error."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "run"],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        # Should fail with exit 2 (config error)
        assert result.returncode == 2
        assert "no steps" in result.stderr.lower() or "config" in result.stderr.lower()

    def test_list_command(self):
        """selftest list should work without config."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "list"],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        # Should succeed (exit 0) even with no config
        assert result.returncode == 0


class TestSelftestCoreWithConfig:
    """Test selftest-core CLI with a config file."""

    @pytest.fixture
    def config_file(self, tmp_path):
        """Create a minimal selftest config for testing."""
        config = tmp_path / "selftest.yaml"
        config.write_text("""
mode: strict
steps:
  - id: echo-test
    tier: kernel
    command: echo hello
    description: Simple echo test
""")
        return config

    def test_plan_with_config(self, config_file):
        """selftest plan --config should show plan."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "plan", "--config", str(config_file)],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        assert result.returncode == 0
        assert "echo-test" in result.stdout
        assert "KERNEL" in result.stdout

    def test_plan_json_with_config(self, config_file):
        """selftest plan --config --json should output valid JSON."""
        import json

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "selftest_core.cli",
                "plan",
                "--config",
                str(config_file),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "steps" in data
        assert len(data["steps"]) == 1
        assert data["steps"][0]["id"] == "echo-test"

    def test_run_with_config(self, config_file):
        """selftest run --config should execute steps."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "run", "--config", str(config_file)],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        # echo command should succeed
        assert result.returncode == 0

    def test_run_json_with_config(self, config_file):
        """selftest run --config --json should output valid JSON."""
        import json

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "selftest_core.cli",
                "run",
                "--config",
                str(config_file),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        # JSON output has passed/failed counts at top level
        assert "passed" in data
        assert "failed" in data
        assert data["passed"] == 1
        assert data["failed"] == 0

    def test_list_with_config(self, config_file):
        """selftest list --config should list steps."""
        result = subprocess.run(
            [sys.executable, "-m", "selftest_core.cli", "list", "--config", str(config_file)],
            capture_output=True,
            text=True,
            cwd=SELFTEST_CORE_DIR / "src",
        )
        assert result.returncode == 0
        assert "echo-test" in result.stdout
        assert "KERNEL" in result.stdout
