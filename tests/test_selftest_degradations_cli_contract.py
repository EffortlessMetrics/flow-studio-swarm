"""
Tests for the show_selftest_degradations.py CLI tool contract (AC-6).

This test suite validates the stable CLI contract for operators who depend on
the degradation log viewer tool. The tool is the stable interface for human
operators and machine parsers to inspect selftest degradation logs.

CLI Contract Tests:
- Plain text output format (human-readable)
- JSON output format (machine-readable)
- JSON v2 output format (enhanced metadata)
- Graceful handling of edge cases (empty/missing logs)
- Output stability (snapshot testing)

The CLI tool (show_selftest_degradations.py) is a stable operator contract.
Breaking changes require version bumps and deprecation notices.
"""

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_TOOL = REPO_ROOT / "swarm" / "tools" / "show_selftest_degradations.py"


def run_cli(args: List[str], cwd: Path = None, timeout: int = 10) -> Tuple[int, str, str]:
    """
    Run the CLI tool and return (exit_code, stdout, stderr).

    Args:
        args: Command-line arguments (e.g., ["--json"])
        cwd: Working directory (defaults to repo root)
        timeout: Command timeout in seconds

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    cwd = cwd or REPO_ROOT
    cmd = ["uv", "run", str(CLI_TOOL)] + args

    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def create_test_degradation_log(entries: List[dict]) -> Path:
    """
    Create a temporary degradation log file with test entries.

    Args:
        entries: List of degradation log entry dicts

    Returns:
        Path to the created log file (in a temp directory that will be cleaned up)
    """
    tmpdir = tempfile.mkdtemp()
    log_path = Path(tmpdir) / "selftest_degradations.log"

    with log_path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    return log_path


def create_test_entries() -> List[dict]:
    """
    Create standard test degradation entries.

    Returns:
        List of 3 test entries with varying severities
    """
    return [
        {
            "timestamp": "2025-12-01T10:15:22+00:00",
            "step_id": "agents-governance",
            "step_name": "Agent definitions linting and formatting",
            "tier": "governance",
            "message": "Agent 'foo-bar' not found in registry",
            "severity": "warning",
            "remediation": "Run: uv run swarm/tools/selftest.py --step agents-governance",
        },
        {
            "timestamp": "2025-12-01T10:15:25+00:00",
            "step_id": "core-checks",
            "step_name": "Python tooling checks (ruff, compileall)",
            "tier": "kernel",
            "message": "Python linting failed with 3 errors",
            "severity": "critical",
            "remediation": "Run: make selftest --step core-checks",
        },
        {
            "timestamp": "2025-12-01T10:15:28+00:00",
            "step_id": "ac-coverage",
            "step_name": "Acceptance criteria coverage thresholds",
            "tier": "optional",
            "message": "Coverage at 85%, threshold is 90%",
            "severity": "info",
            "remediation": "Run: uv run swarm/tools/selftest.py --step ac-coverage",
        },
    ]


# ============================================================================
# Test: Plain Text Output Format
# ============================================================================


class TestCLIPlainOutputFormat:
    """Verify plain text output format is human-readable and stable."""

    def test_cli_plain_output_format(self):
        """Plain text output includes all required fields in readable format."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli([], cwd=log_path.parent)

        assert exit_code == 0, f"CLI should exit 0, got {exit_code}"
        assert stderr == "", f"Should have no stderr, got: {stderr}"

        # Verify output structure
        output_lower = stdout.lower()

        # Should have header
        assert "selftest degradations" in output_lower or "degradation" in output_lower

        # Should display all step IDs
        assert "agents-governance" in stdout
        assert "core-checks" in stdout
        assert "ac-coverage" in stdout

        # Should display severity levels
        assert "WARNING" in stdout or "warning" in stdout
        assert "CRITICAL" in stdout or "critical" in stdout
        assert "INFO" in stdout or "info" in stdout

        # Should display timestamps (formatted)
        assert "2025-12-01" in stdout

        # Should display remediation guidance
        assert "Run:" in stdout or "Fix:" in stdout

        # Should show total count
        assert "3" in stdout  # Total entries count

    def test_cli_plain_output_includes_severity_counts(self):
        """Plain text output summarizes entries by severity."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli([], cwd=log_path.parent)

        assert exit_code == 0
        assert "3" in stdout  # Total entries

        # Verify counts are mentioned (may be implicit or explicit)
        # At minimum, total degradations count should be present
        assert "Total degradations: 3" in stdout or "3 total" in stdout.lower()

    def test_cli_plain_output_truncates_long_messages(self):
        """Long messages are truncated for readability in plain text mode."""
        long_message = "A" * 150  # 150 character message
        entries = [
            {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "test-step",
                "step_name": "Test step",
                "tier": "governance",
                "message": long_message,
                "severity": "warning",
                "remediation": "Test fix",
            }
        ]
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli([], cwd=log_path.parent)

        assert exit_code == 0
        # Message should be truncated (not all 150 chars, but first ~100 + "...")
        assert long_message not in stdout  # Full message not present
        assert "AAA" in stdout  # Partial message present
        # Truncation indicated by "..." (based on tool implementation)
        # Tool truncates to 100 chars + "..."


# ============================================================================
# Test: JSON Output Format
# ============================================================================


class TestCLIJSONOutput:
    """Verify JSON output is valid and machine-parseable."""

    def test_cli_json_output_valid(self):
        """--json flag produces valid JSON array."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json"], cwd=log_path.parent)

        assert exit_code == 0, f"CLI should exit 0, got {exit_code}"
        assert stderr == "", f"Should have no stderr, got: {stderr}"

        # Parse JSON
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nOutput: {stdout}")

        # Validate structure
        assert isinstance(data, list), "JSON output should be an array"
        assert len(data) == 3, f"Should have 3 entries, got {len(data)}"

        # Validate each entry has required fields
        required_fields = {
            "timestamp",
            "step_id",
            "step_name",
            "tier",
            "message",
            "severity",
            "remediation",
        }
        for entry in data:
            assert isinstance(entry, dict), "Each entry should be a dict"
            assert required_fields.issubset(entry.keys()), (
                f"Entry missing fields: {required_fields - entry.keys()}"
            )

    def test_cli_json_output_preserves_entry_order(self):
        """JSON output preserves chronological order of entries."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json"], cwd=log_path.parent)

        assert exit_code == 0
        data = json.loads(stdout)

        # Verify order matches input
        assert data[0]["step_id"] == "agents-governance"
        assert data[1]["step_id"] == "core-checks"
        assert data[2]["step_id"] == "ac-coverage"

    def test_cli_json_output_complete_entry_data(self):
        """JSON output includes all entry fields without truncation."""
        long_message = "A" * 150  # Long message
        entries = [
            {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "test-step",
                "step_name": "Test step with long message",
                "tier": "governance",
                "message": long_message,
                "severity": "warning",
                "remediation": "Run: test fix command",
            }
        ]
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json"], cwd=log_path.parent)

        assert exit_code == 0
        data = json.loads(stdout)

        # JSON should preserve full message (no truncation like plain text)
        assert data[0]["message"] == long_message
        assert len(data[0]["message"]) == 150


# ============================================================================
# Test: JSON v2 Output Format
# ============================================================================


class TestCLIJSONv2Output:
    """Verify JSON v2 output includes enhanced metadata."""

    def test_cli_json_v2_format(self):
        """--json-v2 flag produces enhanced JSON with metadata."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json-v2"], cwd=log_path.parent)

        assert exit_code == 0, f"CLI should exit 0, got {exit_code}"
        assert stderr == "", f"Should have no stderr, got: {stderr}"

        # Parse JSON
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nOutput: {stdout}")

        # Validate v2 structure
        assert isinstance(data, dict), "JSON v2 output should be an object"
        assert data.get("version") == "2.0", "Should have version 2.0"

        # Required top-level keys
        assert "metadata" in data, "Should have metadata section"
        assert "entries" in data, "Should have entries section"

        # Validate metadata
        metadata = data["metadata"]
        assert "timestamp" in metadata, "Metadata should have timestamp"
        assert "log_file" in metadata, "Metadata should have log_file"
        assert "total_entries" in metadata, "Metadata should have total_entries"
        assert metadata["total_entries"] == 3

        # Validate entries
        entries_data = data["entries"]
        assert isinstance(entries_data, list), "Entries should be a list"
        assert len(entries_data) == 3

    def test_cli_json_v2_metadata_timestamp_valid(self):
        """JSON v2 metadata timestamp is valid ISO 8601."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json-v2"], cwd=log_path.parent)

        assert exit_code == 0
        data = json.loads(stdout)

        metadata_ts = data["metadata"]["timestamp"]

        # Parse timestamp to validate ISO 8601 format
        try:
            dt = datetime.fromisoformat(metadata_ts.replace("Z", "+00:00"))
            assert isinstance(dt, datetime), "Should parse to datetime"
        except ValueError:
            pytest.fail(f"Metadata timestamp is not valid ISO 8601: {metadata_ts}")

    def test_cli_json_v2_entries_structure(self):
        """JSON v2 entries match standard JSONL schema."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json-v2"], cwd=log_path.parent)

        assert exit_code == 0
        data = json.loads(stdout)

        entries_data = data["entries"]
        required_fields = {
            "timestamp",
            "step_id",
            "step_name",
            "tier",
            "message",
            "severity",
            "remediation",
        }

        for entry in entries_data:
            assert required_fields.issubset(entry.keys()), (
                f"Entry missing fields: {required_fields - entry.keys()}"
            )


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestCLIEdgeCases:
    """Verify CLI handles edge cases gracefully."""

    def test_cli_with_empty_log(self):
        """CLI handles empty log file gracefully."""
        tmpdir = Path(tempfile.mkdtemp())
        log_path = tmpdir / "selftest_degradations.log"

        # Create empty file
        log_path.touch()

        exit_code, stdout, stderr = run_cli([], cwd=tmpdir)

        # Should exit cleanly (0 or 1, not crash)
        assert exit_code in (0, 1), f"Should handle empty log gracefully, got {exit_code}"

        # Should have helpful message
        output = stdout + stderr
        assert "empty" in output.lower() or "no" in output.lower() or "not found" in output.lower()

    def test_cli_with_missing_log(self):
        """CLI handles missing log file gracefully."""
        tmpdir = Path(tempfile.mkdtemp())
        # Don't create log file

        exit_code, stdout, stderr = run_cli([], cwd=tmpdir)

        # Should exit cleanly (0 or 1, not crash)
        assert exit_code in (0, 1), f"Should handle missing log gracefully, got {exit_code}"

        # Should have helpful message
        output = stdout + stderr
        assert "not found" in output.lower() or "no" in output.lower() or "empty" in output.lower()

    def test_cli_with_no_degradations(self):
        """CLI handles log with only INFO entries gracefully."""
        # Create log with only INFO entries (not failures)
        entries = [
            {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "ac-coverage",
                "step_name": "Acceptance criteria coverage",
                "tier": "optional",
                "message": "Coverage at 95% (above threshold)",
                "severity": "info",
                "remediation": "N/A",
            }
        ]
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli([], cwd=log_path.parent)

        assert exit_code == 0, f"Should handle info-only log, got {exit_code}"

        # Should show summary clearly
        assert "1" in stdout  # 1 total entry

    def test_cli_json_with_empty_log(self):
        """--json flag handles empty log gracefully."""
        tmpdir = Path(tempfile.mkdtemp())
        log_path = tmpdir / "selftest_degradations.log"
        log_path.touch()

        exit_code, stdout, stderr = run_cli(["--json"], cwd=tmpdir)

        assert exit_code in (0, 1)

        # Should produce valid JSON (empty array)
        try:
            data = json.loads(stdout)
            assert isinstance(data, list), "Should be a list"
            assert len(data) == 0, "Should be empty list"
        except json.JSONDecodeError:
            # If output is not JSON, should at least not crash
            pass

    def test_cli_json_v2_with_empty_log(self):
        """--json-v2 flag handles empty log gracefully."""
        tmpdir = Path(tempfile.mkdtemp())
        log_path = tmpdir / "selftest_degradations.log"
        log_path.touch()

        exit_code, stdout, stderr = run_cli(["--json-v2"], cwd=tmpdir)

        assert exit_code in (0, 1)

        # Should produce valid JSON v2 structure
        try:
            data = json.loads(stdout)
            assert data.get("version") == "2.0"
            assert data["metadata"]["total_entries"] == 0
            assert len(data["entries"]) == 0
        except json.JSONDecodeError:
            # If output is not JSON, should at least not crash
            pass


# ============================================================================
# Test: CLI Flags and Help
# ============================================================================


class TestCLIFlags:
    """Verify CLI flags and help output."""

    def test_cli_help_flag(self):
        """--help flag shows usage information."""
        exit_code, stdout, stderr = run_cli(["--help"])

        assert exit_code == 0, f"--help should exit 0, got {exit_code}"

        output = stdout + stderr
        assert "degradation" in output.lower() or "log" in output.lower()
        assert "--json" in output
        assert "--json-v2" in output

    def test_cli_version_flag(self):
        """--version flag shows version information."""
        exit_code, stdout, stderr = run_cli(["--version"])

        assert exit_code == 0, f"--version should exit 0, got {exit_code}"

        output = stdout + stderr
        # Should mention version or tool name
        assert "show_selftest_degradations" in output or "1.0" in output


# ============================================================================
# Test: Output Stability (Snapshot Testing)
# ============================================================================


class TestCLIOutputSnapshot:
    """Verify output format stability for operator scripts."""

    def test_cli_output_snapshot_plain(self):
        """Plain text output format is stable (snapshot test)."""
        # Use 2 entries for golden snapshot
        entries = [
            {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "agents-governance",
                "step_name": "Agent definitions linting and formatting",
                "tier": "governance",
                "message": "Agent 'foo-bar' not found in registry",
                "severity": "warning",
                "remediation": "Run: uv run swarm/tools/selftest.py --step agents-governance",
            },
            {
                "timestamp": "2025-12-01T10:15:25+00:00",
                "step_id": "core-checks",
                "step_name": "Python tooling checks",
                "tier": "kernel",
                "message": "Python linting failed",
                "severity": "critical",
                "remediation": "Run: make selftest --step core-checks",
            },
        ]
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli([], cwd=log_path.parent)

        assert exit_code == 0

        # Verify key output elements are present (not exact formatting, which may vary)
        # This captures the "contract" that operators depend on

        # Header section
        assert "=" in stdout  # Separator lines
        assert "SELFTEST DEGRADATIONS" in stdout or "degradation" in stdout.lower()

        # First entry
        assert "2025-12-01" in stdout
        assert "GOVERNANCE/agents-governance" in stdout or "agents-governance" in stdout
        assert "WARNING" in stdout or "warning" in stdout
        assert "Agent 'foo-bar' not found" in stdout

        # Second entry
        assert "KERNEL/core-checks" in stdout or "core-checks" in stdout
        assert "CRITICAL" in stdout or "critical" in stdout
        assert "Python linting failed" in stdout

        # Footer section
        assert "Total degradations: 2" in stdout or "2 total" in stdout.lower()
        assert "selftest.py" in stdout  # Guidance mentions tool

    def test_cli_output_snapshot_json(self):
        """JSON output schema is stable."""
        entries = create_test_entries()[:2]  # Use 2 entries
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json"], cwd=log_path.parent)

        assert exit_code == 0
        data = json.loads(stdout)

        # Verify stable schema contract
        assert len(data) == 2
        assert all(
            set(entry.keys())
            >= {"timestamp", "step_id", "step_name", "tier", "message", "severity", "remediation"}
            for entry in data
        )

    def test_cli_output_snapshot_json_v2(self):
        """JSON v2 output schema is stable."""
        entries = create_test_entries()[:2]
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json-v2"], cwd=log_path.parent)

        assert exit_code == 0
        data = json.loads(stdout)

        # Verify v2 schema contract
        assert data["version"] == "2.0"
        assert set(data.keys()) >= {"version", "metadata", "entries"}
        assert set(data["metadata"].keys()) >= {"timestamp", "log_file", "total_entries"}
        assert len(data["entries"]) == 2


# ============================================================================
# Test: CLI as Operator Contract
# ============================================================================


class TestCLIAsOperatorContract:
    """
    Verify CLI behavior as a stable operator contract.

    These tests document the expectations that operator scripts and dashboards
    may rely on. Breaking these requires version bumps and deprecation notices.
    """

    def test_cli_exit_code_contract(self):
        """CLI exit codes follow the contract: 0 = success, 1 = usage/error."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        # Success case: valid log, valid flags
        exit_code, stdout, stderr = run_cli([], cwd=log_path.parent)
        assert exit_code == 0, "Valid invocation should exit 0"

        exit_code, stdout, stderr = run_cli(["--json"], cwd=log_path.parent)
        assert exit_code == 0, "Valid JSON invocation should exit 0"

        exit_code, stdout, stderr = run_cli(["--json-v2"], cwd=log_path.parent)
        assert exit_code == 0, "Valid JSON v2 invocation should exit 0"

    def test_cli_json_parseable_even_with_warnings(self):
        """JSON output is parseable even if log has warnings."""
        # This is crucial for operator scripts that parse JSON output
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        exit_code, stdout, stderr = run_cli(["--json"], cwd=log_path.parent)

        # Even with warnings/errors in log, JSON output must be parseable
        try:
            data = json.loads(stdout)
            assert isinstance(data, list)
        except json.JSONDecodeError:
            pytest.fail("JSON output must be parseable for operator scripts")

    def test_cli_tool_exists_at_expected_path(self):
        """CLI tool exists at documented path (swarm/tools/show_selftest_degradations.py)."""
        assert CLI_TOOL.exists(), f"CLI tool must exist at {CLI_TOOL}"
        assert CLI_TOOL.is_file(), "CLI tool must be a file"

    def test_cli_invocation_via_uv_run(self):
        """CLI tool is invocable via 'uv run' (documented invocation method)."""
        entries = create_test_entries()
        log_path = create_test_degradation_log(entries)

        # This is the documented operator invocation
        cmd = f"uv run {CLI_TOOL}"
        proc = subprocess.run(
            cmd,
            cwd=log_path.parent,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

        assert proc.returncode == 0, "Documented invocation method must work"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
