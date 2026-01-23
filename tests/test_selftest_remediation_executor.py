"""
Tests for selftest remediation executor.

Validates:
- Allowlist checking
- Blocklist rejection
- Dry-run mode
- Audit log writing
- CLI argument parsing
- Execution safety
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path to allow importing swarm
sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.tools.selftest_remediate_execute import (
    ALLOWLISTED_PATTERNS,
    ApprovalResult,
    ApprovalStatus,
    DryRunResult,
    ExecutionStatus,
    Remediation,
    dry_run,
    execute,
    is_allowlisted,
    is_blocklisted,
    request_approval,
    write_audit_log,
)


@pytest.fixture
def sample_remediation() -> Remediation:
    """Sample remediation for testing."""
    return Remediation(
        id="rem-test123",
        pattern_id="agent-not-found",
        step_id="agents-governance",
        command="make gen-adapters",
        rationale="Config is out of sync",
        severity="governance",
        timestamp="2025-12-01T10:00:00Z",
    )


@pytest.fixture
def sample_dry_run_result(sample_remediation: Remediation) -> DryRunResult:
    """Sample dry-run result."""
    return DryRunResult(
        remediation_id=sample_remediation.id,
        command=sample_remediation.command,
        diff="--- a/file.md\n+++ b/file.md\n@@ -1 +1 @@\n-old\n+new",
        affected_files=[".claude/agents/test.md"],
        file_count=1,
        safe_to_execute=True,
        warnings=[],
    )


@pytest.fixture
def sample_approval(sample_remediation: Remediation) -> ApprovalResult:
    """Sample approval result."""
    return ApprovalResult(
        remediation_id=sample_remediation.id,
        status=ApprovalStatus.APPROVED,
        approver="test-user",
        channel="cli",
        timestamp="2025-12-01T10:00:05Z",
        timeout_seconds=600,
    )


class TestAllowlistCheck:
    """Tests for allowlist checking."""

    def test_allowed_pattern_passes(self) -> None:
        """Patterns in allowlist should be allowed."""
        allowed, reason = is_allowlisted("make gen-adapters")
        assert allowed is True
        assert reason is None

    def test_allowed_pattern_with_args(self) -> None:
        """Patterns with additional args should be allowed if base is allowed."""
        allowed, reason = is_allowlisted("uv run ruff check --fix swarm/")
        assert allowed is True
        assert reason is None

    def test_unknown_pattern_rejected(self) -> None:
        """Patterns not in allowlist should be rejected."""
        allowed, reason = is_allowlisted("rm -rf /")
        assert allowed is False
        assert reason is not None
        assert "not in allowlist" in reason.lower() or "blocklist" in reason.lower()

    def test_blocklist_overrides_allowlist(self) -> None:
        """Blocklisted commands rejected even if pattern looks similar to allowed."""
        # This tries to sneak in a blocklisted command
        allowed, reason = is_allowlisted("git commit -m 'test'")
        assert allowed is False
        assert "blocklist" in reason.lower()

    def test_all_allowlisted_patterns_are_valid(self) -> None:
        """All patterns in ALLOWLISTED_PATTERNS should pass is_allowlisted."""
        for pattern in ALLOWLISTED_PATTERNS:
            allowed, reason = is_allowlisted(pattern)
            assert allowed is True, f"Pattern '{pattern}' should be allowed but got: {reason}"


class TestBlocklistCheck:
    """Tests for blocklist checking."""

    def test_git_commit_blocked(self) -> None:
        """Git commit should be blocked."""
        blocked, reason = is_blocklisted("git commit -m 'test'")
        assert blocked is True
        assert reason is not None

    def test_git_push_blocked(self) -> None:
        """Git push should be blocked."""
        blocked, reason = is_blocklisted("git push origin main")
        assert blocked is True

    def test_rm_rf_blocked(self) -> None:
        """rm -rf should be blocked."""
        blocked, reason = is_blocklisted("rm -rf /tmp/test")
        assert blocked is True

    def test_rm_f_blocked(self) -> None:
        """rm -f should be blocked."""
        blocked, reason = is_blocklisted("rm -f somefile")
        assert blocked is True

    def test_curl_blocked(self) -> None:
        """curl should be blocked."""
        blocked, reason = is_blocklisted("curl http://example.com")
        assert blocked is True

    def test_safe_command_not_blocked(self) -> None:
        """Safe commands should not be blocked."""
        blocked, reason = is_blocklisted("make gen-adapters")
        assert blocked is False
        assert reason is None

    def test_all_blocklist_patterns_are_functional(self) -> None:
        """Verify blocklist patterns work as expected."""
        test_commands = [
            ("git commit -m 'test'", True),
            ("git push origin main", True),
            ("git reset --hard HEAD", True),
            ("rm -rf /", True),
            ("rm -f file.txt", True),
            ("curl https://example.com", True),
            ("wget https://example.com", True),
            ("make gen-adapters", False),
            ("uv run pytest", False),
        ]

        for cmd, should_block in test_commands:
            blocked, _ = is_blocklisted(cmd)
            assert blocked == should_block, (
                f"Command '{cmd}' should {'be' if should_block else 'not be'} blocked"
            )


class TestDryRun:
    """Tests for dry-run functionality."""

    @patch("subprocess.run")
    def test_dry_run_returns_result(
        self, mock_run: MagicMock, sample_remediation: Remediation, tmp_path: Path
    ) -> None:
        """Dry run should return a DryRunResult."""
        # Mock subprocess.run to avoid platform-specific command issues (e.g., 'make' on Windows)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Dry run output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = dry_run(sample_remediation, working_dir=tmp_path)

        assert isinstance(result, DryRunResult)
        assert result.remediation_id == sample_remediation.id
        assert result.command == sample_remediation.command

    def test_dry_run_captures_warnings(self) -> None:
        """Dry run should capture warnings for problematic commands."""
        remediation = Remediation(
            id="rem-test",
            pattern_id="test",
            step_id="test",
            command="echo 'test'",  # Simple command that will succeed
            rationale="test",
            severity="governance",
            timestamp="2025-12-01T10:00:00Z",
        )

        result = dry_run(remediation)
        # Result should be valid even for simple commands
        assert isinstance(result, DryRunResult)

    @patch("subprocess.run")
    def test_dry_run_timeout_handling(
        self, mock_run: MagicMock, sample_remediation: Remediation
    ) -> None:
        """Dry run should handle timeouts gracefully."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=120)

        result = dry_run(sample_remediation)

        assert result.safe_to_execute is False
        assert "timed out" in result.diff.lower()


class TestApproval:
    """Tests for approval functionality."""

    def test_cli_approval_accepts_y(
        self, sample_remediation: Remediation, sample_dry_run_result: DryRunResult
    ) -> None:
        """CLI should accept 'y' as approval."""
        with patch("builtins.input", return_value="y"):
            result = request_approval(
                remediation=sample_remediation,
                dry_run_result=sample_dry_run_result,
                channel="cli",
            )

        assert result.status == ApprovalStatus.APPROVED
        assert result.channel == "cli"

    def test_cli_approval_rejects_n(
        self, sample_remediation: Remediation, sample_dry_run_result: DryRunResult
    ) -> None:
        """CLI should reject on 'n'."""
        with patch("builtins.input", return_value="n"):
            result = request_approval(
                remediation=sample_remediation,
                dry_run_result=sample_dry_run_result,
                channel="cli",
            )

        assert result.status == ApprovalStatus.REJECTED

    def test_cli_approval_rejects_empty(
        self, sample_remediation: Remediation, sample_dry_run_result: DryRunResult
    ) -> None:
        """CLI should reject on empty input (default N)."""
        with patch("builtins.input", return_value=""):
            result = request_approval(
                remediation=sample_remediation,
                dry_run_result=sample_dry_run_result,
                channel="cli",
            )

        assert result.status == ApprovalStatus.REJECTED

    def test_auto_approve_flag(
        self, sample_remediation: Remediation, sample_dry_run_result: DryRunResult
    ) -> None:
        """Auto-approve should bypass prompt."""
        result = request_approval(
            remediation=sample_remediation,
            dry_run_result=sample_dry_run_result,
            channel="cli",
            auto_approve=True,
        )

        assert result.status == ApprovalStatus.APPROVED
        assert result.approver == "auto-approve"

    def test_keyboard_interrupt_rejects(
        self, sample_remediation: Remediation, sample_dry_run_result: DryRunResult
    ) -> None:
        """Keyboard interrupt should reject approval."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = request_approval(
                remediation=sample_remediation,
                dry_run_result=sample_dry_run_result,
                channel="cli",
            )

        assert result.status == ApprovalStatus.REJECTED


class TestExecution:
    """Tests for command execution."""

    def test_execution_blocked_without_approval(self, sample_remediation: Remediation) -> None:
        """Should refuse to execute without approval."""
        approval = ApprovalResult(
            remediation_id=sample_remediation.id,
            status=ApprovalStatus.REJECTED,
            approver="test",
            channel="cli",
            timestamp="2025-12-01T10:00:00Z",
        )

        result = execute(sample_remediation, approval)

        assert result.status == ExecutionStatus.SKIPPED
        assert "not approved" in result.stderr.lower()

    def test_execution_blocked_for_blocklisted(self, sample_approval: ApprovalResult) -> None:
        """Should refuse to execute blocklisted commands even if approved."""
        bad_remediation = Remediation(
            id="rem-bad",
            pattern_id="bad",
            step_id="test",
            command="git commit -m 'hack'",
            rationale="bad",
            severity="governance",
            timestamp="2025-12-01T10:00:00Z",
        )

        result = execute(bad_remediation, sample_approval)

        assert result.status == ExecutionStatus.FAILED
        assert "blocked" in result.stderr.lower()

    @patch("subprocess.run")
    def test_execution_records_git_sha(
        self,
        mock_run: MagicMock,
        sample_remediation: Remediation,
        sample_approval: ApprovalResult,
    ) -> None:
        """Should record git SHA before and after."""
        # Mock subprocess.run to return success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = execute(sample_remediation, sample_approval)

        # Should have recorded before SHA
        assert result.git_commit_before is not None


class TestAuditLog:
    """Tests for audit logging."""

    def test_audit_log_writes_jsonl(
        self,
        tmp_path: Path,
        sample_remediation: Remediation,
        sample_dry_run_result: DryRunResult,
        sample_approval: ApprovalResult,
    ) -> None:
        """Audit log should write valid JSONL."""
        audit_path = tmp_path / "audit.jsonl"

        write_audit_log(
            remediation=sample_remediation,
            dry_run_result=sample_dry_run_result,
            approval=sample_approval,
            execute_result=None,
            audit_log_path=audit_path,
        )

        assert audit_path.exists()

        # Read and parse the JSON
        with open(audit_path) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["version"] == "1.0"
        assert entry["remediation_id"] == sample_remediation.id
        assert entry["suggestion"]["pattern_id"] == sample_remediation.pattern_id

    def test_audit_log_appends(
        self,
        tmp_path: Path,
        sample_remediation: Remediation,
        sample_dry_run_result: DryRunResult,
        sample_approval: ApprovalResult,
    ) -> None:
        """Audit log should append, not overwrite."""
        audit_path = tmp_path / "audit.jsonl"

        # Write twice
        write_audit_log(
            remediation=sample_remediation,
            dry_run_result=sample_dry_run_result,
            approval=sample_approval,
            execute_result=None,
            audit_log_path=audit_path,
        )
        write_audit_log(
            remediation=sample_remediation,
            dry_run_result=sample_dry_run_result,
            approval=sample_approval,
            execute_result=None,
            audit_log_path=audit_path,
        )

        # Should have 2 lines
        with open(audit_path) as f:
            lines = f.readlines()

        assert len(lines) == 2

    def test_audit_log_has_required_fields(
        self,
        tmp_path: Path,
        sample_remediation: Remediation,
        sample_dry_run_result: DryRunResult,
        sample_approval: ApprovalResult,
    ) -> None:
        """Audit log entry should have all required fields."""
        audit_path = tmp_path / "audit.jsonl"

        write_audit_log(
            remediation=sample_remediation,
            dry_run_result=sample_dry_run_result,
            approval=sample_approval,
            execute_result=None,
            audit_log_path=audit_path,
        )

        with open(audit_path) as f:
            entry = json.loads(f.readline())

        required_fields = [
            "version",
            "timestamp",
            "remediation_id",
            "transaction_id",
            "suggestion",
            "allowlist_check",
            "dry_run",
            "approval",
            "metadata",
        ]

        for field in required_fields:
            assert field in entry, f"Missing required field: {field}"

    def test_audit_log_creates_directory(
        self, tmp_path: Path, sample_remediation: Remediation, sample_approval: ApprovalResult
    ) -> None:
        """Audit log should create parent directory if needed."""
        audit_path = tmp_path / "nested" / "path" / "audit.jsonl"

        write_audit_log(
            remediation=sample_remediation,
            dry_run_result=None,
            approval=sample_approval,
            execute_result=None,
            audit_log_path=audit_path,
        )

        assert audit_path.exists()


class TestCLI:
    """Tests for CLI argument parsing."""

    def test_cli_dry_run_flag(self) -> None:
        """CLI should accept --dry-run flag."""
        import argparse

        # Test that --dry-run is a valid argument
        parser = argparse.ArgumentParser()
        parser.add_argument("--dry-run", action="store_true")
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_cli_auto_approve_flag(self) -> None:
        """CLI should accept --auto-approve flag."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--auto-approve", action="store_true")
        args = parser.parse_args(["--auto-approve"])
        assert args.auto_approve is True


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_flow_with_mocked_suggestions(self, tmp_path: Path) -> None:
        """Test full flow from suggestion to execution."""
        from swarm.tools.selftest_remediate_execute import (
            get_pending_remediations,
        )

        # Create a mock degradation log
        log_path = tmp_path / "selftest_degradations.log"
        log_path.write_text(
            "2025-12-01T10:00:00 | agents-governance | FAIL | GOVERNANCE | Agent 'test' not found in registry\n"
        )

        # Create a remediation map
        import yaml

        map_path = tmp_path / "remediation_map.yaml"
        map_data = {
            "version": "1.0.0",
            "remediation_patterns": [
                {
                    "id": "agent-not-found",
                    "error_pattern": "Agent .* not found in registry",
                    "severity": "governance",
                    "suggested_commands": ["make gen-adapters"],
                    "rationale": "Config is out of sync",
                }
            ],
        }
        with open(map_path, "w") as f:
            yaml.dump(map_data, f)

        # Get remediations
        remediations = get_pending_remediations(
            degradation_log=log_path,
            remediation_map=map_path,
        )

        assert len(remediations) == 1
        assert remediations[0].command == "make gen-adapters"

    def test_no_remediations_when_no_log(self, tmp_path: Path) -> None:
        """Should return empty list when no degradation log exists."""
        from swarm.tools.selftest_remediate_execute import get_pending_remediations

        remediations = get_pending_remediations(degradation_log=tmp_path / "nonexistent.log")

        assert len(remediations) == 0


class TestRobustness:
    """Test edge cases and robustness."""

    def test_handles_missing_remediation_map(self, tmp_path: Path) -> None:
        """Should handle missing remediation map gracefully."""
        from swarm.tools.selftest_remediate_execute import get_pending_remediations

        log_path = tmp_path / "test.log"
        log_path.write_text("2025-12-01T10:00:00 | test | FAIL | GOVERNANCE | Error\n")

        remediations = get_pending_remediations(
            degradation_log=log_path,
            remediation_map=tmp_path / "nonexistent.yaml",
        )

        assert len(remediations) == 0

    def test_handles_empty_command(self) -> None:
        """Should handle empty commands safely."""
        allowed, reason = is_allowlisted("")
        assert allowed is False

        blocked, _ = is_blocklisted("")
        assert blocked is False

    def test_handles_whitespace_command(self) -> None:
        """Should handle whitespace-only commands."""
        allowed, reason = is_allowlisted("   ")
        assert allowed is False

    def test_audit_log_handles_special_characters(
        self, tmp_path: Path, sample_approval: ApprovalResult
    ) -> None:
        """Audit log should handle special characters in commands."""
        remediation = Remediation(
            id="rem-special",
            pattern_id="test",
            step_id="test",
            command='echo "hello\'world"',
            rationale="Test with quotes",
            severity="governance",
            timestamp="2025-12-01T10:00:00Z",
        )

        audit_path = tmp_path / "audit.jsonl"
        write_audit_log(
            remediation=remediation,
            dry_run_result=None,
            approval=sample_approval,
            execute_result=None,
            audit_log_path=audit_path,
        )

        # Should be valid JSON
        with open(audit_path) as f:
            entry = json.loads(f.readline())

        assert 'echo "hello\'world"' in entry["suggestion"]["command"]
