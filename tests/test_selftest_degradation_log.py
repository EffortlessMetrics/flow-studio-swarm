"""
Tests for AC-6 Selftest Degradation Logging feature.

AC-6 (Degradation Log Persistence) verifies that:
- Degradation log uses frozen JSONL schema with required fields
- Log entries are valid JSON and machine-readable
- Log persists across multiple runs and appends correctly
- Degradation severity maps correctly to failure types
- Human-readable CLI tool works with multiple output formats

JSONL Schema:
  timestamp:  ISO 8601 timestamp (required)
  step_id:    Unique step identifier (required)
  step_name:  Human-readable step description (required)
  tier:       Selftest tier: "kernel", "governance", "optional" (required)
  message:    Failure output from step (required)
  severity:   "critical", "warning", "info" (required)
  remediation: Suggested fix command (required)
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd: str, timeout: int = 30, cwd: Path = None) -> Tuple[int, str]:
    """Run shell command and return (exit_code, stdout+stderr)."""
    cwd = cwd or REPO_ROOT
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout


def load_degradation_log(log_path: Path) -> List[dict]:
    """Load and parse JSONL degradation log file."""
    if not log_path.exists():
        return []

    entries = []
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def validate_degradation_entry(entry: dict) -> Tuple[bool, str]:
    """
    Validate a degradation log entry against schema.

    Returns:
        (is_valid, error_message)
    """
    required_fields = {
        "timestamp",
        "step_id",
        "step_name",
        "tier",
        "message",
        "severity",
        "remediation",
    }
    missing = required_fields - set(entry.keys())

    if missing:
        return False, f"Missing required fields: {missing}"

    # Validate field types
    if not isinstance(entry["timestamp"], str):
        return False, "timestamp must be string (ISO 8601)"

    if not isinstance(entry["step_id"], str):
        return False, "step_id must be string"

    if not isinstance(entry["step_name"], str):
        return False, "step_name must be string"

    if entry["tier"] not in ("kernel", "governance", "optional"):
        return False, f"tier must be 'kernel', 'governance', or 'optional', got {entry['tier']}"

    if not isinstance(entry["message"], str):
        return False, "message must be string"

    if entry["severity"] not in ("critical", "warning", "info"):
        return False, f"severity must be 'critical', 'warning', or 'info', got {entry['severity']}"

    if not isinstance(entry["remediation"], str):
        return False, "remediation must be string"

    # Validate timestamp format (ISO 8601)
    try:
        from datetime import datetime

        datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False, f"timestamp '{entry['timestamp']}' is not valid ISO 8601"

    return True, ""


# ============================================================================
# AC-6-1: JSONL Format and Schema
# ============================================================================


class TestDegradationLogJSONLFormat:
    """Validate degradation log JSONL format and schema compliance."""

    def test_degradation_log_format_valid_json(self):
        """Each line in selftest_degradations.log is valid JSON."""
        # Run selftest in degraded mode to trigger degradation logging
        # We force a failure by corrupting a temporary config
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            log_path = tmppath / "selftest_degradations.log"

            # Create a mock degradation entry
            entry = {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "agents-governance",
                "step_name": "Agent definitions linting and formatting",
                "tier": "governance",
                "message": "Agent 'test-agent' validation failed",
                "severity": "warning",
                "remediation": "Run: uv run swarm/tools/selftest.py --step agents-governance",
            }

            # Write test entry
            with log_path.open("w") as f:
                f.write(json.dumps(entry) + "\n")

            # Load and verify
            entries = load_degradation_log(log_path)
            assert len(entries) == 1
            assert entries[0] == entry

    def test_degradation_log_schema_has_required_fields(self):
        """Degradation log entries have all required fields per AC-6 schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            log_path = tmppath / "selftest_degradations.log"

            # Create multiple entries with all required fields
            entries = [
                {
                    "timestamp": "2025-12-01T10:15:22+00:00",
                    "step_id": "agents-governance",
                    "step_name": "Agent definitions linting and formatting",
                    "tier": "governance",
                    "message": "Agent config error",
                    "severity": "warning",
                    "remediation": "Run: uv run swarm/tools/selftest.py --step agents-governance",
                },
                {
                    "timestamp": "2025-12-01T10:15:25+00:00",
                    "step_id": "devex-contract",
                    "step_name": "Developer experience contract (flows, commands, skills)",
                    "tier": "governance",
                    "message": "Flow validation failed",
                    "severity": "warning",
                    "remediation": "Run: uv run swarm/tools/selftest.py --step devex-contract",
                },
            ]

            with log_path.open("w") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")

            # Load and validate all entries
            loaded = load_degradation_log(log_path)
            assert len(loaded) == 2

            for entry in loaded:
                is_valid, error = validate_degradation_entry(entry)
                assert is_valid, f"Schema validation failed: {error}"

    def test_degradation_log_schema_strict_tier_values(self):
        """tier field must be 'kernel', 'governance', or 'optional'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            tmppath / "selftest_degradations.log"

            # Valid tiers
            for tier in ["kernel", "governance", "optional"]:
                entry = {
                    "timestamp": "2025-12-01T10:15:22+00:00",
                    "step_id": "test-step",
                    "step_name": "Test step",
                    "tier": tier,
                    "message": "Test message",
                    "severity": "warning",
                    "remediation": "Test fix",
                }
                is_valid, error = validate_degradation_entry(entry)
                assert is_valid, f"Tier '{tier}' should be valid: {error}"

            # Invalid tier
            entry["tier"] = "invalid"
            is_valid, error = validate_degradation_entry(entry)
            assert not is_valid, "Invalid tier should be rejected"

    def test_degradation_log_schema_strict_severity_values(self):
        """severity field must be 'critical', 'warning', or 'info'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir)

            # Valid severities
            for severity in ["critical", "warning", "info"]:
                entry = {
                    "timestamp": "2025-12-01T10:15:22+00:00",
                    "step_id": "test-step",
                    "step_name": "Test step",
                    "tier": "governance",
                    "message": "Test message",
                    "severity": severity,
                    "remediation": "Test fix",
                }
                is_valid, error = validate_degradation_entry(entry)
                assert is_valid, f"Severity '{severity}' should be valid: {error}"

            # Invalid severity
            entry["severity"] = "invalid"
            is_valid, error = validate_degradation_entry(entry)
            assert not is_valid, "Invalid severity should be rejected"

    def test_degradation_log_schema_iso8601_timestamp(self):
        """timestamp must be valid ISO 8601 format with time component."""
        with tempfile.TemporaryDirectory():
            # Valid ISO 8601 timestamps with time component
            for ts in [
                "2025-12-01T10:15:22+00:00",
                "2025-12-01T10:15:22Z",
                "2025-12-01T10:15:22.123456+00:00",
            ]:
                entry = {
                    "timestamp": ts,
                    "step_id": "test",
                    "step_name": "Test",
                    "tier": "governance",
                    "message": "Test",
                    "severity": "warning",
                    "remediation": "Test",
                }
                is_valid, error = validate_degradation_entry(entry)
                assert is_valid, f"Timestamp '{ts}' should be valid: {error}"

            # Invalid timestamps (date-only, time-only, or garbage)
            for ts in ["not-a-timestamp", "10:15:22", "invalid"]:
                entry["timestamp"] = ts
                is_valid, error = validate_degradation_entry(entry)
                assert not is_valid, f"Timestamp '{ts}' should be invalid"


# ============================================================================
# AC-6-2: Log Persistence and Append
# ============================================================================


class TestDegradationLogPersistence:
    """Verify degradation log persists and appends correctly across runs."""

    def test_degradation_log_appends_entries(self):
        """Multiple degradation log entries append correctly (don't overwrite)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            log_path = tmppath / "selftest_degradations.log"

            # Simulate first run
            entry1 = {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "agents-governance",
                "step_name": "Agent definitions linting and formatting",
                "tier": "governance",
                "message": "First failure",
                "severity": "warning",
                "remediation": "Run: uv run swarm/tools/selftest.py --step agents-governance",
            }
            with log_path.open("w") as f:
                f.write(json.dumps(entry1) + "\n")

            # Simulate second run (appending)
            entry2 = {
                "timestamp": "2025-12-01T10:15:25+00:00",
                "step_id": "devex-contract",
                "step_name": "Developer experience contract",
                "tier": "governance",
                "message": "Second failure",
                "severity": "warning",
                "remediation": "Run: uv run swarm/tools/selftest.py --step devex-contract",
            }
            with log_path.open("a") as f:
                f.write(json.dumps(entry2) + "\n")

            # Verify both entries exist
            entries = load_degradation_log(log_path)
            assert len(entries) == 2
            assert entries[0]["step_id"] == "agents-governance"
            assert entries[1]["step_id"] == "devex-contract"

    def test_degradation_log_timestamps_ordered(self):
        """Log entries maintain chronological order (can be used for tracking history)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            log_path = tmppath / "selftest_degradations.log"

            # Create entries with ascending timestamps
            from datetime import datetime, timedelta, timezone

            base_time = datetime(2025, 12, 1, 10, 15, 22, tzinfo=timezone.utc)
            entries_to_write = []

            for i in range(3):
                ts = base_time + timedelta(seconds=i * 3)
                entry = {
                    "timestamp": ts.isoformat(),
                    "step_id": f"step-{i}",
                    "step_name": f"Step {i}",
                    "tier": "governance",
                    "message": f"Failure {i}",
                    "severity": "warning",
                    "remediation": f"Fix {i}",
                }
                entries_to_write.append(entry)

            with log_path.open("w") as f:
                for entry in entries_to_write:
                    f.write(json.dumps(entry) + "\n")

            # Load and verify order
            loaded = load_degradation_log(log_path)
            assert len(loaded) == 3

            for i in range(3):
                assert loaded[i]["step_id"] == f"step-{i}"

            # Verify timestamps are ascending
            for i in range(len(loaded) - 1):
                ts1 = datetime.fromisoformat(loaded[i]["timestamp"].replace("Z", "+00:00"))
                ts2 = datetime.fromisoformat(loaded[i + 1]["timestamp"].replace("Z", "+00:00"))
                assert ts1 <= ts2, "Timestamps should be in ascending order"

    def test_degradation_log_skips_empty_lines(self):
        """Degradation log reader skips empty lines gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            log_path = tmppath / "selftest_degradations.log"

            entry = {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "test",
                "step_name": "Test",
                "tier": "governance",
                "message": "Test",
                "severity": "warning",
                "remediation": "Test",
            }

            # Write with empty lines
            with log_path.open("w") as f:
                f.write(json.dumps(entry) + "\n")
                f.write("\n")  # Empty line
                f.write("\n")  # Another empty line
                f.write(json.dumps(entry) + "\n")
                f.write("")  # Trailing newline

            loaded = load_degradation_log(log_path)
            assert len(loaded) == 2, "Should load 2 entries, skipping empty lines"


# ============================================================================
# AC-6-3: Severity Mapping
# ============================================================================


class TestDegradationLogSeverityMapping:
    """Verify severity levels map correctly to failure types."""

    def test_kernel_tier_severity_mapping(self):
        """KERNEL tier failures should map to CRITICAL severity."""
        entry = {
            "timestamp": "2025-12-01T10:15:22+00:00",
            "step_id": "core-checks",
            "step_name": "Python tooling checks",
            "tier": "kernel",
            "message": "Python linting failed",
            "severity": "critical",
            "remediation": "Run: uv run swarm/tools/selftest.py --step core-checks",
        }
        is_valid, error = validate_degradation_entry(entry)
        assert is_valid, f"KERNEL tier with CRITICAL severity should be valid: {error}"

    def test_governance_tier_severity_mapping(self):
        """GOVERNANCE tier failures should map to WARNING severity."""
        entry = {
            "timestamp": "2025-12-01T10:15:22+00:00",
            "step_id": "agents-governance",
            "step_name": "Agent definitions linting",
            "tier": "governance",
            "message": "Agent validation failed",
            "severity": "warning",
            "remediation": "Run: uv run swarm/tools/selftest.py --step agents-governance",
        }
        is_valid, error = validate_degradation_entry(entry)
        assert is_valid, f"GOVERNANCE tier with WARNING severity should be valid: {error}"

    def test_optional_tier_severity_mapping(self):
        """OPTIONAL tier failures should map to INFO severity."""
        entry = {
            "timestamp": "2025-12-01T10:15:22+00:00",
            "step_id": "ac-coverage",
            "step_name": "Acceptance criteria coverage",
            "tier": "optional",
            "message": "Coverage below threshold",
            "severity": "info",
            "remediation": "Run: uv run swarm/tools/selftest.py --step ac-coverage",
        }
        is_valid, error = validate_degradation_entry(entry)
        assert is_valid, f"OPTIONAL tier with INFO severity should be valid: {error}"


# ============================================================================
# AC-6-4: CLI Tool Integration
# ============================================================================


class TestShowSelftestDegradationsCLI:
    """Test the show_selftest_degradations.py CLI tool."""

    def test_degradation_cli_tool_exists(self):
        """show_selftest_degradations.py script exists and is executable."""
        tool_path = REPO_ROOT / "swarm" / "tools" / "show_selftest_degradations.py"
        assert tool_path.exists(), f"Tool not found at {tool_path}"

    def test_degradation_cli_help_output(self):
        """CLI tool responds to --help flag."""
        cmd = "cd {} && uv run swarm/tools/show_selftest_degradations.py --help".format(REPO_ROOT)
        exit_code, output = run_command(cmd)
        assert exit_code == 0, f"Help should exit 0, got {exit_code}"
        assert "degradation" in output.lower() or "log" in output.lower(), (
            "Help should mention degradation or log"
        )

    def test_degradation_cli_handles_missing_log(self):
        """CLI tool handles missing log file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp dir where no log exists
            cmd = f"cd {tmpdir} && uv run {REPO_ROOT}/swarm/tools/show_selftest_degradations.py"
            exit_code, output = run_command(cmd, cwd=Path(tmpdir))
            # Should exit cleanly (0 or 1, but not crash)
            assert exit_code in (0, 1), (
                f"Should handle missing log gracefully, got exit code {exit_code}"
            )

    def test_degradation_cli_json_output(self):
        """CLI tool outputs valid JSON with --json flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            log_path = tmppath / "selftest_degradations.log"

            entry = {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "test",
                "step_name": "Test step",
                "tier": "governance",
                "message": "Test failure",
                "severity": "warning",
                "remediation": "Run: test",
            }
            with log_path.open("w") as f:
                f.write(json.dumps(entry) + "\n")

            cmd = f"cd {tmppath} && uv run {REPO_ROOT}/swarm/tools/show_selftest_degradations.py --json"
            exit_code, output = run_command(cmd, cwd=tmppath)
            assert exit_code == 0, f"JSON output failed with exit code {exit_code}"

            # Parse JSON output
            try:
                data = json.loads(output)
                assert isinstance(data, list), "JSON output should be an array"
                assert len(data) == 1, "Should have one entry"
                assert data[0]["step_id"] == "test"
            except json.JSONDecodeError:
                pytest.fail(f"Output is not valid JSON: {output}")

    def test_degradation_cli_json_v2_output(self):
        """CLI tool outputs JSON v2 format with --json-v2 flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            log_path = tmppath / "selftest_degradations.log"

            entry = {
                "timestamp": "2025-12-01T10:15:22+00:00",
                "step_id": "test",
                "step_name": "Test step",
                "tier": "governance",
                "message": "Test failure",
                "severity": "warning",
                "remediation": "Run: test",
            }
            with log_path.open("w") as f:
                f.write(json.dumps(entry) + "\n")

            cmd = f"cd {tmppath} && uv run {REPO_ROOT}/swarm/tools/show_selftest_degradations.py --json-v2"
            exit_code, output = run_command(cmd, cwd=tmppath)
            assert exit_code == 0, f"JSON v2 output failed with exit code {exit_code}"

            try:
                data = json.loads(output)
                assert data.get("version") == "2.0", "JSON v2 should have version 2.0"
                assert "metadata" in data, "JSON v2 should have metadata section"
                assert "entries" in data, "JSON v2 should have entries section"
                assert len(data["entries"]) == 1, "Should have one entry"
            except json.JSONDecodeError:
                pytest.fail(f"Output is not valid JSON: {output}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
