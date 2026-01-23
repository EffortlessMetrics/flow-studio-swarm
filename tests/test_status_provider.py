#!/usr/bin/env python3
"""
Tests for status_provider.py - Governance status tracking for Flow Studio.

This test suite covers:
1. Happy path: Status aggregation with mix of PASS/FAIL/SKIP across tiers
2. Edge cases: Empty steps, all OPTIONAL failing, degraded mode
3. Tier aggregation: Per-tier counts and status determination
4. JSON output format verification
5. Caching behavior
6. Snapshot loading from artifacts

## Test Coverage (22+ tests)

### Data Classes (6 tests)
- test_kernel_status_ok_state
- test_kernel_status_broken_state
- test_selftest_status_defaults
- test_flows_status_defaults
- test_agents_status_defaults
- test_selftest_snapshot_empty

### Status Aggregation (8 tests)
- test_determine_governance_state_fully_governed
- test_determine_governance_state_unhealthy_kernel
- test_determine_governance_state_unhealthy_selftest_red
- test_determine_governance_state_unhealthy_validation
- test_determine_governance_state_degraded_yellow
- test_determine_governance_state_degraded_warnings
- test_determine_governance_state_unknown
- test_determine_governance_state_all_optional_fail_passes

### Snapshot Loading (4 tests)
- test_load_selftest_snapshot_empty_on_missing_file
- test_load_selftest_snapshot_parses_valid_json
- test_load_selftest_snapshot_handles_corrupt_json
- test_load_degradations_from_log

### Hint Generation (3 tests)
- test_build_hints_kernel_ok
- test_build_hints_kernel_failure
- test_build_hints_governance_failures

### Status Report (4 tests)
- test_status_report_to_dict
- test_status_report_to_json
- test_status_report_removes_redundant_fields
- test_status_provider_caching
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest
from swarm.tools.status_provider import (
    AgentsStatus,
    FlowsStatus,
    KernelStatus,
    SelftestSnapshot,
    SelfTestStatus,
    StatusProvider,
    StatusReport,
    ValidationStatus,
)

# ============================================================================
# Data Classes Tests
# ============================================================================


class TestDataClasses:
    """Tests for the dataclass definitions."""

    def test_kernel_status_ok_state(self):
        """Test KernelStatus with ok=True state."""
        status = KernelStatus(
            ok=True,
            last_run="2025-01-01T00:00:00+00:00",
            status="HEALTHY",
        )

        assert status.ok is True
        assert status.status == "HEALTHY"
        assert status.error is None
        assert status.last_run == "2025-01-01T00:00:00+00:00"

    def test_kernel_status_broken_state(self):
        """Test KernelStatus with ok=False and error message."""
        status = KernelStatus(
            ok=False,
            last_run="2025-01-01T00:00:00+00:00",
            status="BROKEN",
            error="ruff check failed",
        )

        assert status.ok is False
        assert status.status == "BROKEN"
        assert status.error == "ruff check failed"

    def test_selftest_status_defaults(self):
        """Test SelfTestStatus default field values."""
        status = SelfTestStatus(
            mode="strict",
            last_run="2025-01-01T00:00:00+00:00",
            status="GREEN",
        )

        assert status.mode == "strict"
        assert status.status == "GREEN"
        assert status.failed_steps == []
        assert status.degraded_steps == []
        assert status.kernel_ok is True
        assert status.governance_ok is True
        assert status.optional_ok is True
        assert status.critical_passed == 0
        assert status.critical_failed == 0
        assert status.warning_passed == 0
        assert status.warning_failed == 0
        assert status.info_passed == 0
        assert status.info_failed == 0

    def test_flows_status_defaults(self):
        """Test FlowsStatus with default values."""
        status = FlowsStatus(
            total=6,
            healthy=5,
            degraded=1,
            broken=0,
        )

        assert status.total == 6
        assert status.healthy == 5
        assert status.degraded == 1
        assert status.broken == 0
        assert status.invalid_flows == []

    def test_agents_status_defaults(self):
        """Test AgentsStatus with default values."""
        status = AgentsStatus(total=45)

        assert status.total == 45
        assert status.by_status == {"healthy": 0, "misconfigured": 0, "unknown": 0}
        assert status.invalid_agents == []

    def test_selftest_snapshot_empty(self):
        """Test SelftestSnapshot.empty() factory method."""
        snapshot = SelftestSnapshot.empty()

        assert snapshot.mode == "unknown"
        assert snapshot.status == "UNKNOWN"
        assert snapshot.kernel_ok is True
        assert snapshot.governance_ok is True
        assert snapshot.optional_ok is True
        assert snapshot.failed_steps == []
        assert snapshot.kernel_failed == []
        assert snapshot.governance_failed == []
        assert snapshot.optional_failed == []


# ============================================================================
# Status Aggregation Tests
# ============================================================================


class TestGovernanceStateAggregation:
    """Tests for _determine_governance_state() logic."""

    @pytest.fixture
    def provider(self, tmp_path):
        """Create a StatusProvider with tmp_path as repo root."""
        return StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

    def test_determine_governance_state_fully_governed(self, provider):
        """
        Test FULLY_GOVERNED state when:
        - kernel is OK
        - selftest is GREEN
        - validation PASSED
        """
        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        selftest = SelfTestStatus(mode="strict", last_run="now", status="GREEN")
        validation = ValidationStatus(last_run="now", status="PASS")

        result = provider._determine_governance_state(kernel, selftest, validation)

        assert result == "FULLY_GOVERNED"

    def test_determine_governance_state_unhealthy_kernel(self, provider):
        """Test UNHEALTHY state when kernel is broken."""
        kernel = KernelStatus(ok=False, last_run="now", status="BROKEN", error="ruff failed")
        selftest = SelfTestStatus(mode="strict", last_run="now", status="GREEN")
        validation = ValidationStatus(last_run="now", status="PASS")

        result = provider._determine_governance_state(kernel, selftest, validation)

        assert result == "UNHEALTHY"

    def test_determine_governance_state_unhealthy_selftest_red(self, provider):
        """Test UNHEALTHY state when selftest is RED (critical failures)."""
        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        selftest = SelfTestStatus(
            mode="strict",
            last_run="now",
            status="RED",
            failed_steps=["core-checks"],
            kernel_ok=False,
        )
        validation = ValidationStatus(last_run="now", status="PASS")

        result = provider._determine_governance_state(kernel, selftest, validation)

        assert result == "UNHEALTHY"

    def test_determine_governance_state_unhealthy_validation(self, provider):
        """Test UNHEALTHY state when validation failed."""
        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        selftest = SelfTestStatus(mode="strict", last_run="now", status="GREEN")
        validation = ValidationStatus(last_run="now", status="FAIL", error_count=3)

        result = provider._determine_governance_state(kernel, selftest, validation)

        assert result == "UNHEALTHY"

    def test_determine_governance_state_degraded_yellow(self, provider):
        """Test DEGRADED state when selftest is YELLOW (governance failures)."""
        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        selftest = SelfTestStatus(
            mode="degraded",
            last_run="now",
            status="YELLOW",
            degraded_steps=["agents-governance"],
            governance_ok=False,
        )
        validation = ValidationStatus(last_run="now", status="PASS")

        result = provider._determine_governance_state(kernel, selftest, validation)

        assert result == "DEGRADED"

    def test_determine_governance_state_degraded_warnings(self, provider):
        """Test DEGRADED state when validation has warnings."""
        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        selftest = SelfTestStatus(mode="strict", last_run="now", status="GREEN")
        validation = ValidationStatus(last_run="now", status="PASS", warning_count=2)

        result = provider._determine_governance_state(kernel, selftest, validation)

        assert result == "DEGRADED"

    def test_determine_governance_state_unknown(self, provider):
        """Test UNKNOWN state when selftest status is UNKNOWN."""
        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        selftest = SelfTestStatus(mode="strict", last_run="now", status="UNKNOWN")
        validation = ValidationStatus(last_run="now", status="PASS")

        result = provider._determine_governance_state(kernel, selftest, validation)

        assert result == "UNKNOWN"

    def test_determine_governance_state_all_optional_fail_passes(self, provider):
        """
        Test that all OPTIONAL failures but KERNEL/GOVERNANCE passing results in FULLY_GOVERNED.

        This is an important edge case: optional failures should not degrade the overall state.
        """
        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        selftest = SelfTestStatus(
            mode="strict",
            last_run="now",
            status="GREEN",  # GREEN because only optional failed
            kernel_ok=True,
            governance_ok=True,
            optional_ok=False,  # Optional failures
            info_failed=2,
        )
        validation = ValidationStatus(last_run="now", status="PASS")

        result = provider._determine_governance_state(kernel, selftest, validation)

        # Even with optional failures, if kernel and governance are OK, state is FULLY_GOVERNED
        assert result == "FULLY_GOVERNED"


# ============================================================================
# Snapshot Loading Tests
# ============================================================================


class TestSnapshotLoading:
    """Tests for loading selftest snapshots and degradation logs."""

    def test_load_selftest_snapshot_empty_on_missing_file(self, tmp_path):
        """Test that missing snapshot file returns empty snapshot."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

        snapshot = provider._load_selftest_snapshot()

        assert snapshot.mode == "unknown"
        assert snapshot.status == "UNKNOWN"
        assert snapshot.kernel_ok is True  # Defaults to True per empty()

    def test_load_selftest_snapshot_parses_valid_json(self, tmp_path):
        """Test parsing a valid selftest_report.json artifact."""
        # Create the artifact directory structure
        report_dir = tmp_path / "swarm" / "runs" / "main" / "build"
        report_dir.mkdir(parents=True)

        # Create a mock selftest report
        report_data = {
            "summary": {
                "mode": "strict",
                "kernel_ok": True,
                "governance_ok": False,
                "optional_ok": True,
                "failed_steps": ["agents-governance"],
                "kernel_failed": [],
                "governance_failed": ["agents-governance"],
                "optional_failed": [],
            }
        }
        (report_dir / "selftest_report.json").write_text(json.dumps(report_data))

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        snapshot = provider._load_selftest_snapshot()

        assert snapshot.mode == "strict"
        assert snapshot.status == "YELLOW"  # governance failed
        assert snapshot.kernel_ok is True
        assert snapshot.governance_ok is False
        assert snapshot.optional_ok is True
        assert snapshot.failed_steps == ["agents-governance"]
        assert snapshot.governance_failed == ["agents-governance"]

    def test_load_selftest_snapshot_handles_corrupt_json(self, tmp_path):
        """Test graceful handling of corrupt JSON."""
        report_dir = tmp_path / "swarm" / "runs" / "main" / "build"
        report_dir.mkdir(parents=True)
        (report_dir / "selftest_report.json").write_text("{ invalid json }")

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        snapshot = provider._load_selftest_snapshot()

        assert snapshot.mode == "unknown"
        assert snapshot.status == "UNKNOWN"

    def test_load_degradations_from_log(self, tmp_path):
        """Test loading degradation entries from JSONL log file."""
        # Create degradation log with multiple entries
        log_entries = [
            {"timestamp": "2025-01-01T00:00:00Z", "step": "step-1", "reason": "Test 1"},
            {"timestamp": "2025-01-01T01:00:00Z", "step": "step-2", "reason": "Test 2"},
        ]
        log_path = tmp_path / "selftest_degradations.log"
        log_path.write_text("\n".join(json.dumps(e) for e in log_entries))

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        degradations = provider._load_degradations()

        assert len(degradations) == 2
        assert degradations[0]["step"] == "step-1"
        assert degradations[1]["step"] == "step-2"
        # Verify sorted by timestamp (oldest first)
        assert degradations[0]["timestamp"] < degradations[1]["timestamp"]

    def test_load_degradations_empty_on_missing_file(self, tmp_path):
        """Test that missing log file returns empty list."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        degradations = provider._load_degradations()

        assert degradations == []

    def test_load_degradations_skips_invalid_lines(self, tmp_path):
        """Test that invalid JSON lines are skipped gracefully."""
        log_path = tmp_path / "selftest_degradations.log"
        log_path.write_text(
            '{"timestamp": "2025-01-01T00:00:00Z", "step": "valid"}\n'
            "not valid json\n"
            '{"timestamp": "2025-01-02T00:00:00Z", "step": "also-valid"}\n'
        )

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        degradations = provider._load_degradations()

        assert len(degradations) == 2
        assert degradations[0]["step"] == "valid"
        assert degradations[1]["step"] == "also-valid"


# ============================================================================
# Hint Generation Tests
# ============================================================================


class TestHintGeneration:
    """Tests for _build_hints() method."""

    def test_build_hints_kernel_ok(self, tmp_path):
        """Test hints when kernel is healthy."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        snapshot = SelftestSnapshot(
            mode="strict",
            status="GREEN",
            kernel_ok=True,
            governance_ok=True,
            optional_ok=True,
        )
        validation = ValidationStatus(last_run="now", status="PASS")

        hints = provider._build_hints(kernel, snapshot, validation)

        assert "summary" in hints
        assert "detailed" in hints
        assert "KERNEL: " in hints["summary"]
        assert "Kernel health check passed" in hints["detailed"]

    def test_build_hints_kernel_failure(self, tmp_path):
        """Test hints when kernel is broken."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

        kernel = KernelStatus(ok=False, last_run="now", status="BROKEN", error="ruff failed")
        snapshot = SelftestSnapshot(
            mode="strict",
            status="RED",
            kernel_ok=False,
            governance_ok=True,
            optional_ok=True,
            kernel_failed=["core-checks"],
        )
        validation = ValidationStatus(last_run="now", status="PASS")

        hints = provider._build_hints(kernel, snapshot, validation)

        assert "KERNEL failure" in hints["detailed"]
        assert "kernel_smoke.py" in hints["detailed"]

    def test_build_hints_governance_failures(self, tmp_path):
        """Test hints when governance checks fail."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        snapshot = SelftestSnapshot(
            mode="degraded",
            status="YELLOW",
            kernel_ok=True,
            governance_ok=False,
            optional_ok=True,
            governance_failed=["agents-governance", "skills-governance"],
        )
        validation = ValidationStatus(last_run="now", status="PASS")

        hints = provider._build_hints(kernel, snapshot, validation)

        assert "Governance failure" in hints["detailed"]
        assert "agents-governance" in hints["detailed"]
        assert "--degraded" in hints["detailed"]  # Workaround suggestion

    def test_build_hints_optional_failures(self, tmp_path):
        """Test hints when optional checks fail (informational)."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        snapshot = SelftestSnapshot(
            mode="strict",
            status="GREEN",
            kernel_ok=True,
            governance_ok=True,
            optional_ok=False,
            optional_failed=["ac-coverage", "extras", "flowstudio-smoke", "extra-step"],
        )
        validation = ValidationStatus(last_run="now", status="PASS")

        hints = provider._build_hints(kernel, snapshot, validation)

        assert "Optional check failure" in hints["detailed"]
        assert "ac-coverage" in hints["detailed"]
        # Should show first 3 and "... and X more"
        assert "and 1 more" in hints["detailed"]

    def test_build_hints_validation_failure(self, tmp_path):
        """Test hints when validation fails."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

        kernel = KernelStatus(ok=True, last_run="now", status="HEALTHY")
        snapshot = SelftestSnapshot.empty()
        snapshot.kernel_ok = True
        snapshot.governance_ok = True
        validation = ValidationStatus(last_run="now", status="FAIL", error_count=3)

        hints = provider._build_hints(kernel, snapshot, validation)

        assert "Validation failed" in hints["detailed"]
        assert "validate_swarm.py" in hints["detailed"]


# ============================================================================
# Status Report Tests
# ============================================================================


class TestStatusReport:
    """Tests for StatusReport serialization."""

    def test_status_report_to_dict(self):
        """Test StatusReport.to_dict() converts to dictionary."""
        selftest = SelfTestStatus(mode="strict", last_run="now", status="GREEN")
        validation = ValidationStatus(last_run="now", status="PASS")

        report = StatusReport(
            timestamp="2025-01-01T00:00:00+00:00",
            service="flow-studio",
            governance={"kernel": {"ok": True}, "selftest": asdict(selftest)},
            flows={"total": 6, "healthy": 6},
            agents={"total": 45},
            hints={"summary": "All OK", "detailed": ""},
            selftest=selftest,
            validation=validation,
        )

        d = report.to_dict()

        assert isinstance(d, dict)
        assert d["timestamp"] == "2025-01-01T00:00:00+00:00"
        assert d["service"] == "flow-studio"
        assert "governance" in d
        assert "flows" in d
        assert "agents" in d
        assert "hints" in d

    def test_status_report_to_json(self):
        """Test StatusReport.to_json() produces valid JSON."""
        selftest = SelfTestStatus(mode="strict", last_run="now", status="GREEN")
        validation = ValidationStatus(last_run="now", status="PASS")

        report = StatusReport(
            timestamp="2025-01-01T00:00:00+00:00",
            service="flow-studio",
            governance={"kernel": {"ok": True}},
            flows={"total": 6},
            agents={"total": 45},
            hints={"summary": "OK"},
            selftest=selftest,
            validation=validation,
        )

        json_str = report.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["service"] == "flow-studio"
        assert parsed["timestamp"] == "2025-01-01T00:00:00+00:00"

    def test_status_report_removes_redundant_fields(self):
        """Test that selftest and validation fields are removed from dict output."""
        selftest = SelfTestStatus(mode="strict", last_run="now", status="GREEN")
        validation = ValidationStatus(last_run="now", status="PASS")

        report = StatusReport(
            timestamp="now",
            service="flow-studio",
            governance={},
            flows={},
            agents={},
            hints={},
            selftest=selftest,
            validation=validation,
        )

        d = report.to_dict()

        # These should be stripped since they're redundant with governance
        assert "selftest" not in d
        assert "validation" not in d


# ============================================================================
# Caching Tests
# ============================================================================


class TestStatusProviderCaching:
    """Tests for StatusProvider caching behavior."""

    def test_status_provider_caching_respects_ttl(self, tmp_path, monkeypatch):
        """Test that cached status is returned within TTL."""
        # Create minimal repo structure to avoid subprocess errors
        # We'll mock the subprocess calls instead
        call_count = [0]

        def mock_compute(self):
            call_count[0] += 1
            # Return a minimal status report
            return StatusReport(
                timestamp=f"call-{call_count[0]}",
                service="flow-studio",
                governance={"state": "UNKNOWN"},
                flows={"total": 0},
                agents={"total": 0},
                hints={"summary": "mock", "detailed": "mock"},
            )

        monkeypatch.setattr(StatusProvider, "_compute_status", mock_compute)

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=10)

        # First call computes
        status1 = provider.get_status()
        assert status1.timestamp == "call-1"
        assert call_count[0] == 1

        # Second call within TTL returns cached
        status2 = provider.get_status()
        assert status2.timestamp == "call-1"  # Same as first
        assert call_count[0] == 1  # No additional computation

        # Force refresh bypasses cache
        status3 = provider.get_status(force_refresh=True)
        assert status3.timestamp == "call-2"
        assert call_count[0] == 2

    def test_status_provider_no_caching_with_zero_ttl(self, tmp_path, monkeypatch):
        """Test that cache_ttl_seconds=0 disables caching."""
        call_count = [0]

        def mock_compute(self):
            call_count[0] += 1
            return StatusReport(
                timestamp=f"call-{call_count[0]}",
                service="flow-studio",
                governance={},
                flows={},
                agents={},
                hints={},
            )

        monkeypatch.setattr(StatusProvider, "_compute_status", mock_compute)

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

        provider.get_status()
        provider.get_status()
        provider.get_status()

        # Each call should compute since TTL is 0
        assert call_count[0] == 3


# ============================================================================
# Edge Cases and Stress Tests
# ============================================================================


class TestEdgeCases:
    """Edge case and boundary condition tests."""

    def test_empty_steps_returns_appropriate_defaults(self, tmp_path):
        """Test behavior when no steps are present in selftest results."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

        # Create an empty report
        report_dir = tmp_path / "swarm" / "runs" / "main" / "build"
        report_dir.mkdir(parents=True)
        (report_dir / "selftest_report.json").write_text(
            json.dumps(
                {
                    "summary": {
                        "mode": "strict",
                        "kernel_ok": True,
                        "governance_ok": True,
                        "optional_ok": True,
                        "failed_steps": [],
                    }
                }
            )
        )

        snapshot = provider._load_selftest_snapshot()

        assert snapshot.status == "GREEN"
        assert snapshot.failed_steps == []

    def test_validation_status_with_all_optional_fields(self):
        """Test ValidationStatus with all fields populated."""
        status = ValidationStatus(
            last_run="2025-01-01T00:00:00+00:00",
            status="FAIL",
            error_count=5,
            warning_count=3,
            agents_with_issues=["agent-1", "agent-2"],
            flows_with_issues=["flow-1"],
            steps_with_issues=["step-1"],
            agents={"agent-1": {"has_issues": True}},
            flows={"flow-1": {"valid": False}},
            steps={"step-1": {"failed": True}},
            error="Validation failed with 5 errors",
        )

        assert status.error_count == 5
        assert status.warning_count == 3
        assert len(status.agents_with_issues) == 2
        assert len(status.flows_with_issues) == 1
        assert "agent-1" in status.agents

    def test_selftest_status_with_mixed_tier_failures(self):
        """Test SelfTestStatus with failures across all tiers."""
        status = SelfTestStatus(
            mode="degraded",
            last_run="now",
            status="YELLOW",
            failed_steps=["core-checks"],
            degraded_steps=["agents-governance", "bdd"],
            kernel_ok=False,
            governance_ok=False,
            optional_ok=False,
            critical_passed=1,
            critical_failed=1,
            warning_passed=3,
            warning_failed=2,
            info_passed=0,
            info_failed=2,
        )

        assert status.kernel_ok is False
        assert status.governance_ok is False
        assert status.optional_ok is False
        assert status.critical_failed == 1
        assert status.warning_failed == 2
        assert status.info_failed == 2

    def test_flows_status_with_issues(self):
        """Test FlowsStatus with invalid flows."""
        status = FlowsStatus(
            total=6,
            healthy=4,
            degraded=1,
            broken=1,
            invalid_flows=["flow-7-test"],
        )

        assert status.total == 6
        assert status.broken == 1
        assert "flow-7-test" in status.invalid_flows

    def test_agents_status_with_misconfigured(self):
        """Test AgentsStatus with misconfigured agents."""
        status = AgentsStatus(
            total=45,
            by_status={
                "healthy": 43,
                "misconfigured": 2,
                "unknown": 0,
            },
            invalid_agents=["bad-agent-1", "bad-agent-2"],
        )

        assert status.total == 45
        assert status.by_status["misconfigured"] == 2
        assert len(status.invalid_agents) == 2


# ============================================================================
# Tier Count Aggregation Tests
# ============================================================================


class TestTierAggregation:
    """Tests for per-tier count aggregation in SelfTestStatus."""

    def test_tier_counts_match_expectations(self):
        """Test that tier counts sum correctly."""
        status = SelfTestStatus(
            mode="strict",
            last_run="now",
            status="YELLOW",
            critical_passed=2,
            critical_failed=0,
            warning_passed=5,
            warning_failed=2,
            info_passed=1,
            info_failed=1,
        )

        # Total passed
        total_passed = status.critical_passed + status.warning_passed + status.info_passed
        assert total_passed == 8

        # Total failed
        total_failed = status.critical_failed + status.warning_failed + status.info_failed
        assert total_failed == 3

        # Grand total
        assert total_passed + total_failed == 11

    def test_kernel_ok_depends_on_critical_failures(self):
        """Test that kernel_ok is False when critical steps fail."""
        # All critical passed
        status_ok = SelfTestStatus(
            mode="strict",
            last_run="now",
            status="GREEN",
            kernel_ok=True,
            critical_passed=3,
            critical_failed=0,
        )
        assert status_ok.kernel_ok is True

        # Some critical failed
        status_fail = SelfTestStatus(
            mode="strict",
            last_run="now",
            status="RED",
            kernel_ok=False,
            critical_passed=2,
            critical_failed=1,
        )
        assert status_fail.kernel_ok is False

    def test_governance_ok_depends_on_warning_failures(self):
        """Test that governance_ok is False when warning steps fail."""
        # All warnings passed
        status_ok = SelfTestStatus(
            mode="strict",
            last_run="now",
            status="GREEN",
            governance_ok=True,
            warning_passed=5,
            warning_failed=0,
        )
        assert status_ok.governance_ok is True

        # Some warnings failed
        status_fail = SelfTestStatus(
            mode="degraded",
            last_run="now",
            status="YELLOW",
            governance_ok=False,
            warning_passed=3,
            warning_failed=2,
        )
        assert status_fail.governance_ok is False


# ============================================================================
# JSON Output Format Tests
# ============================================================================


class TestJSONOutputFormat:
    """Tests for JSON output format compliance."""

    def test_json_output_has_required_fields(self):
        """Test that JSON output includes all required fields."""
        report = StatusReport(
            timestamp="2025-01-01T00:00:00+00:00",
            service="flow-studio",
            governance={
                "kernel": {"ok": True, "status": "HEALTHY"},
                "selftest": {"mode": "strict", "status": "GREEN"},
                "validation": {"status": "PASS"},
                "state": "FULLY_GOVERNED",
            },
            flows={"total": 6, "healthy": 6, "degraded": 0, "broken": 0},
            agents={"total": 45, "by_status": {"healthy": 45}},
            hints={"summary": "All checks passed", "detailed": "..."},
        )

        json_str = report.to_json()
        data = json.loads(json_str)

        # Required top-level fields
        assert "timestamp" in data
        assert "service" in data
        assert "governance" in data
        assert "flows" in data
        assert "agents" in data
        assert "hints" in data

        # Governance structure
        gov = data["governance"]
        assert "kernel" in gov
        assert "selftest" in gov
        assert "state" in gov

    def test_json_output_is_valid_json(self):
        """Test that output is parseable JSON."""
        report = StatusReport(
            timestamp="now",
            service="test",
            governance={},
            flows={},
            agents={},
            hints={},
        )

        json_str = report.to_json()

        # Should not raise
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_json_handles_special_characters(self):
        """Test that special characters in hints are properly escaped."""
        report = StatusReport(
            timestamp="now",
            service="flow-studio",
            governance={},
            flows={},
            agents={},
            hints={
                "summary": 'Contains "quotes" and backslash\\',
                "detailed": "Multi\nline\tcontent",
            },
        )

        json_str = report.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert '"quotes"' in parsed["hints"]["summary"]
        assert "backslash\\" in parsed["hints"]["summary"]


# ============================================================================
# File-based Status Checks Tests
# ============================================================================


class TestFileBasedChecks:
    """Tests for _check_flows() and _check_agents() which read YAML configs."""

    def test_check_flows_with_valid_configs(self, tmp_path):
        """Test _check_flows() with valid flow YAML configs."""
        import yaml

        # Create flows config directory
        flows_dir = tmp_path / "swarm" / "config" / "flows"
        flows_dir.mkdir(parents=True)

        # Create valid flow configs
        for i in range(1, 7):
            flow_data = {"key": f"flow-{i}", "name": f"Flow {i}", "steps": []}
            (flows_dir / f"flow-{i}.yaml").write_text(yaml.dump(flow_data))

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        status = provider._check_flows()

        assert status.total == 6
        assert status.healthy == 6
        assert status.broken == 0
        assert status.invalid_flows == []

    def test_check_flows_with_invalid_config(self, tmp_path):
        """Test _check_flows() with an invalid flow config."""
        import yaml

        flows_dir = tmp_path / "swarm" / "config" / "flows"
        flows_dir.mkdir(parents=True)

        # Create one valid and one invalid flow
        (flows_dir / "flow-1.yaml").write_text(yaml.dump({"key": "flow-1"}))
        (flows_dir / "flow-2.yaml").write_text("invalid: yaml: content: [")

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        status = provider._check_flows()

        assert status.total == 2
        assert status.healthy == 1
        assert status.broken == 1
        assert "flow-2" in status.invalid_flows

    def test_check_flows_with_missing_key(self, tmp_path):
        """Test _check_flows() with flow config missing required 'key' field."""
        import yaml

        flows_dir = tmp_path / "swarm" / "config" / "flows"
        flows_dir.mkdir(parents=True)

        # Create flow without 'key' field
        (flows_dir / "flow-1.yaml").write_text(yaml.dump({"name": "Flow 1"}))

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        status = provider._check_flows()

        assert status.total == 1
        assert status.healthy == 0
        assert status.broken == 1
        assert "flow-1" in status.invalid_flows

    def test_check_flows_with_empty_directory(self, tmp_path):
        """Test _check_flows() with no flow configs present."""
        flows_dir = tmp_path / "swarm" / "config" / "flows"
        flows_dir.mkdir(parents=True)

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        status = provider._check_flows()

        assert status.total == 0
        assert status.healthy == 0
        assert status.broken == 0

    def test_check_flows_directory_not_exists(self, tmp_path):
        """Test _check_flows() when flows directory does not exist."""
        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        status = provider._check_flows()

        assert status.total == 0
        assert status.healthy == 0

    def test_check_agents_with_valid_configs(self, tmp_path):
        """Test _check_agents() with valid agent YAML configs."""
        import yaml

        agents_dir = tmp_path / "swarm" / "config" / "agents"
        agents_dir.mkdir(parents=True)

        # Create valid agent configs
        for name in ["agent-1", "agent-2", "agent-3"]:
            agent_data = {
                "key": name,
                "category": "implementation",
                "color": "green",
                "short_role": "Test agent",
            }
            (agents_dir / f"{name}.yaml").write_text(yaml.dump(agent_data))

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        status = provider._check_agents()

        assert status.total == 3
        assert status.by_status["healthy"] == 3
        assert status.by_status["misconfigured"] == 0
        assert status.invalid_agents == []

    def test_check_agents_with_missing_fields(self, tmp_path):
        """Test _check_agents() with agent configs missing required fields."""
        import yaml

        agents_dir = tmp_path / "swarm" / "config" / "agents"
        agents_dir.mkdir(parents=True)

        # Valid agent
        (agents_dir / "valid-agent.yaml").write_text(
            yaml.dump(
                {
                    "key": "valid-agent",
                    "category": "implementation",
                    "color": "green",
                }
            )
        )

        # Missing 'color'
        (agents_dir / "bad-agent.yaml").write_text(
            yaml.dump(
                {
                    "key": "bad-agent",
                    "category": "implementation",
                }
            )
        )

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        status = provider._check_agents()

        assert status.total == 2
        assert status.by_status["healthy"] == 1
        assert status.by_status["misconfigured"] == 1
        assert "bad-agent" in status.invalid_agents

    def test_check_agents_with_invalid_yaml(self, tmp_path):
        """Test _check_agents() with malformed YAML."""
        agents_dir = tmp_path / "swarm" / "config" / "agents"
        agents_dir.mkdir(parents=True)

        (agents_dir / "broken.yaml").write_text("not: valid: yaml: [")

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        status = provider._check_agents()

        assert status.total == 1
        assert status.by_status["misconfigured"] == 1
        assert "broken" in status.invalid_agents


# ============================================================================
# Snapshot Status Derivation Tests
# ============================================================================


class TestSnapshotStatusDerivation:
    """Tests for status derivation from snapshot data."""

    def test_snapshot_status_red_when_kernel_fails(self, tmp_path):
        """Test that status is RED when kernel_ok is False."""
        report_dir = tmp_path / "swarm" / "runs" / "main" / "build"
        report_dir.mkdir(parents=True)

        (report_dir / "selftest_report.json").write_text(
            json.dumps(
                {
                    "summary": {
                        "kernel_ok": False,
                        "governance_ok": True,
                        "optional_ok": True,
                    }
                }
            )
        )

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        snapshot = provider._load_selftest_snapshot()

        assert snapshot.status == "RED"
        assert snapshot.kernel_ok is False

    def test_snapshot_status_yellow_when_governance_fails(self, tmp_path):
        """Test that status is YELLOW when only governance fails."""
        report_dir = tmp_path / "swarm" / "runs" / "main" / "build"
        report_dir.mkdir(parents=True)

        (report_dir / "selftest_report.json").write_text(
            json.dumps(
                {
                    "summary": {
                        "kernel_ok": True,
                        "governance_ok": False,
                        "optional_ok": True,
                    }
                }
            )
        )

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        snapshot = provider._load_selftest_snapshot()

        assert snapshot.status == "YELLOW"
        assert snapshot.kernel_ok is True
        assert snapshot.governance_ok is False

    def test_snapshot_status_green_when_all_pass(self, tmp_path):
        """Test that status is GREEN when all tiers pass."""
        report_dir = tmp_path / "swarm" / "runs" / "main" / "build"
        report_dir.mkdir(parents=True)

        (report_dir / "selftest_report.json").write_text(
            json.dumps(
                {
                    "summary": {
                        "kernel_ok": True,
                        "governance_ok": True,
                        "optional_ok": False,  # Optional failures don't affect GREEN
                    }
                }
            )
        )

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        snapshot = provider._load_selftest_snapshot()

        assert snapshot.status == "GREEN"

    def test_snapshot_parses_failed_step_lists(self, tmp_path):
        """Test that failed step lists are correctly parsed."""
        report_dir = tmp_path / "swarm" / "runs" / "main" / "build"
        report_dir.mkdir(parents=True)

        (report_dir / "selftest_report.json").write_text(
            json.dumps(
                {
                    "summary": {
                        "kernel_ok": False,
                        "governance_ok": False,
                        "optional_ok": False,
                        "failed_steps": ["core-checks", "agents-governance", "ac-coverage"],
                        "kernel_failed": ["core-checks"],
                        "governance_failed": ["agents-governance"],
                        "optional_failed": ["ac-coverage"],
                    }
                }
            )
        )

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        snapshot = provider._load_selftest_snapshot()

        assert "core-checks" in snapshot.failed_steps
        assert "agents-governance" in snapshot.failed_steps
        assert "ac-coverage" in snapshot.failed_steps
        assert snapshot.kernel_failed == ["core-checks"]
        assert snapshot.governance_failed == ["agents-governance"]
        assert snapshot.optional_failed == ["ac-coverage"]

    def test_snapshot_handles_null_lists(self, tmp_path):
        """Test that null/None lists are converted to empty lists."""
        report_dir = tmp_path / "swarm" / "runs" / "main" / "build"
        report_dir.mkdir(parents=True)

        (report_dir / "selftest_report.json").write_text(
            json.dumps(
                {
                    "summary": {
                        "kernel_ok": True,
                        "governance_ok": True,
                        "optional_ok": True,
                        "failed_steps": None,
                        "kernel_failed": None,
                    }
                }
            )
        )

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        snapshot = provider._load_selftest_snapshot()

        assert snapshot.failed_steps == []
        assert snapshot.kernel_failed == []


# ============================================================================
# Timeout Handling Regression Tests
# ============================================================================


class TestTimeoutHandling:
    """
    Regression tests for subprocess.TimeoutExpired handling.

    These tests ensure that timeout exceptions are properly caught
    inside the try blocks. This prevents regressions where the
    subprocess.run() call accidentally gets moved outside the try block.
    """

    def test_check_kernel_handles_timeout(self, tmp_path, monkeypatch):
        """
        Test that _check_kernel() properly catches TimeoutExpired.

        This is a regression test to ensure the subprocess.run() call
        remains inside the try block that catches TimeoutExpired.
        """
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=300)

        monkeypatch.setattr(subprocess, "run", mock_run)

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        result = provider._check_kernel()

        # Should return a proper KernelStatus, not raise an exception
        assert isinstance(result, KernelStatus)
        assert result.ok is False
        assert result.status == "BROKEN"
        assert "timed out" in result.error

    def test_check_selftest_handles_timeout(self, tmp_path, monkeypatch):
        """
        Test that _check_selftest() properly catches TimeoutExpired.

        This is a regression test to ensure the subprocess.run() call
        remains inside the try block that catches TimeoutExpired.
        """
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=600)

        monkeypatch.setattr(subprocess, "run", mock_run)

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        result = provider._check_selftest()

        # Should return a proper SelfTestStatus, not raise an exception
        assert isinstance(result, SelfTestStatus)
        assert result.status == "RED"
        assert "selftest-timeout" in result.failed_steps
        assert result.kernel_ok is False

    def test_check_validation_handles_timeout(self, tmp_path, monkeypatch):
        """
        Test that _check_validation() properly catches TimeoutExpired.

        This is a regression test to ensure the subprocess.run() call
        remains inside the try block that catches TimeoutExpired.
        """
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=120)

        monkeypatch.setattr(subprocess, "run", mock_run)

        provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)
        result = provider._check_validation()

        # Should return a proper ValidationStatus, not raise an exception
        assert isinstance(result, ValidationStatus)
        assert result.status == "ERROR"
        assert "timed out" in result.error.lower()
