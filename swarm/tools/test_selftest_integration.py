#!/usr/bin/env python3
"""
Integration tests for selftest system.

Tests cover:
- Severity/category schema
- Report JSON export
- Artifact manager
- Selftest orchestration
- Override manager
- Doctor diagnostics
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from artifact_manager import ArtifactManager, get_hostname, get_platform_name
from override_manager import OverrideManager

# Import the modules under test
from selftest_config import (
    SELFTEST_STEPS,
    SelfTestCategory,
    SelfTestSeverity,
    SelfTestStep,
    SelfTestTier,
    get_step_by_id,
    get_steps_in_order,
    validate_step_list,
)
from selftest_doctor import SelfTestDoctor
from selftest_report_schema import (
    SelfTestReport,
    SelfTestReportMetadata,
    SelfTestStepResult,
    SelfTestSummary,
)


class TestSelfTestSchema:
    """Test severity/category schema."""

    def test_all_steps_have_severity(self):
        """Every step has severity classification."""
        for step in SELFTEST_STEPS:
            assert hasattr(step, "severity")
            assert step.severity in [
                SelfTestSeverity.CRITICAL,
                SelfTestSeverity.WARNING,
                SelfTestSeverity.INFO,
            ]

    def test_all_steps_have_category(self):
        """Every step has category classification."""
        for step in SELFTEST_STEPS:
            assert hasattr(step, "category")
            assert step.category in [
                SelfTestCategory.SECURITY,
                SelfTestCategory.PERFORMANCE,
                SelfTestCategory.CORRECTNESS,
                SelfTestCategory.GOVERNANCE,
            ]

    def test_step_to_dict_includes_severity_category(self):
        """Step.to_dict() includes severity and category."""
        step = SELFTEST_STEPS[0]
        step_dict = step.to_dict()
        assert "severity" in step_dict
        assert "category" in step_dict
        assert step_dict["severity"] == step.severity.value
        assert step_dict["category"] == step.category.value

    def test_validate_step_list_passes(self):
        """Step list validation passes."""
        errors = validate_step_list()
        assert len(errors) == 0

    def test_severity_enum_values(self):
        """Severity enum has correct values."""
        assert SelfTestSeverity.CRITICAL.value == "critical"
        assert SelfTestSeverity.WARNING.value == "warning"
        assert SelfTestSeverity.INFO.value == "info"

    def test_category_enum_values(self):
        """Category enum has correct values."""
        assert SelfTestCategory.SECURITY.value == "security"
        assert SelfTestCategory.PERFORMANCE.value == "performance"
        assert SelfTestCategory.CORRECTNESS.value == "correctness"
        assert SelfTestCategory.GOVERNANCE.value == "governance"

    def test_tier_enum_values(self):
        """Tier enum has correct values."""
        assert SelfTestTier.KERNEL.value == "kernel"
        assert SelfTestTier.GOVERNANCE.value == "governance"
        assert SelfTestTier.OPTIONAL.value == "optional"


class TestSelfTestStepDefinition:
    """Test individual step properties."""

    def test_step_to_dict_complete(self):
        """Step dictionary has all required fields."""
        step = SELFTEST_STEPS[0]
        step_dict = step.to_dict()
        required_fields = [
            "id",
            "description",
            "tier",
            "severity",
            "category",
            "command",
            "allow_fail_in_degraded",
            "dependencies",
        ]
        for field in required_fields:
            assert field in step_dict, f"Missing field: {field}"

    def test_step_full_command_joins_with_and(self):
        """Step.full_command() joins commands with &&."""
        step = SELFTEST_STEPS[0]
        full_cmd = step.full_command()
        assert isinstance(full_cmd, str)
        assert " && " in full_cmd or len(step.command) == 1

    def test_step_dependencies_initialized(self):
        """Step dependencies default to empty list."""
        step = SelfTestStep(
            id="test-step",
            description="Test",
            tier=SelfTestTier.KERNEL,
            severity=SelfTestSeverity.CRITICAL,
            category=SelfTestCategory.CORRECTNESS,
            command=["true"],
        )
        assert step.dependencies == []

    def test_step_validation_requires_id(self):
        """Step creation fails without id."""
        with pytest.raises(ValueError, match="id and description"):
            SelfTestStep(
                id="",
                description="Test",
                tier=SelfTestTier.KERNEL,
                severity=SelfTestSeverity.CRITICAL,
                category=SelfTestCategory.CORRECTNESS,
                command=["true"],
            )

    def test_step_validation_requires_command(self):
        """Step creation fails without command."""
        with pytest.raises(ValueError, match="command must be"):
            SelfTestStep(
                id="test",
                description="Test",
                tier=SelfTestTier.KERNEL,
                severity=SelfTestSeverity.CRITICAL,
                category=SelfTestCategory.CORRECTNESS,
                command=[],
            )

    def test_step_validation_requires_severity_enum(self):
        """Step creation validates severity is enum."""
        with pytest.raises(ValueError, match="severity must be"):
            SelfTestStep(
                id="test",
                description="Test",
                tier=SelfTestTier.KERNEL,
                severity="critical",  # string, not enum
                category=SelfTestCategory.CORRECTNESS,
                command=["true"],
            )


class TestReportSchema:
    """Test JSON report schema."""

    def test_report_metadata_creation(self):
        """Create valid metadata."""
        metadata = SelfTestReportMetadata(
            run_id="test-run",
            timestamp=datetime.now(timezone.utc).isoformat(),
            hostname="test-host",
            platform="linux",
            git_branch="main",
            git_commit="abc123",
            user="testuser",
            mode="strict",
        )
        assert metadata.run_id == "test-run"
        assert metadata.platform == "linux"
        assert metadata.mode == "strict"

    def test_report_step_result_creation(self):
        """Create valid step result."""
        result = SelfTestStepResult(
            step_id="core-checks",
            description="Test step",
            tier="kernel",
            severity="critical",
            category="correctness",
            status="PASS",
            exit_code=0,
            duration_ms=1000,
            command="test",
            timestamp_start=1234567890.0,
            timestamp_end=1234567891.0,
        )
        assert result.step_id == "core-checks"
        assert result.status == "PASS"
        assert result.exit_code == 0

    def test_report_summary_creation(self):
        """Create valid summary."""
        summary = SelfTestSummary(
            passed=8,
            failed=1,
            skipped=1,
            total=10,
            critical_passed=1,
            critical_failed=0,
            warning_passed=5,
            warning_failed=1,
            info_passed=2,
            info_failed=0,
            category_security_passed=0,
            category_security_failed=0,
            category_performance_passed=0,
            category_performance_failed=0,
            category_correctness_passed=2,
            category_correctness_failed=0,
            category_governance_passed=6,
            category_governance_failed=1,
            total_duration_ms=15000,
        )
        assert summary.passed == 8
        assert summary.failed == 1
        assert summary.total == 10

    def test_report_to_json(self):
        """Report serializes to valid JSON."""
        metadata = SelfTestReportMetadata(
            run_id="test",
            timestamp=datetime.now(timezone.utc).isoformat(),
            hostname="test",
            platform="linux",
            git_branch="main",
            git_commit="abc123",
            user="test",
            mode="strict",
        )
        step_result = SelfTestStepResult(
            step_id="core-checks",
            description="Test step",
            tier="kernel",
            severity="critical",
            category="correctness",
            status="PASS",
            exit_code=0,
            duration_ms=1000,
            command="test",
            timestamp_start=1234567890.0,
            timestamp_end=1234567891.0,
        )
        summary = SelfTestSummary(
            passed=1,
            failed=0,
            skipped=0,
            total=1,
            critical_passed=1,
            critical_failed=0,
            warning_passed=0,
            warning_failed=0,
            info_passed=0,
            info_failed=0,
            category_security_passed=0,
            category_security_failed=0,
            category_performance_passed=0,
            category_performance_failed=0,
            category_correctness_passed=1,
            category_correctness_failed=0,
            category_governance_passed=0,
            category_governance_failed=0,
            total_duration_ms=1000,
        )
        report = SelfTestReport(metadata=metadata, results=[step_result], summary=summary)
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["metadata"]["run_id"] == "test"
        assert len(parsed["results"]) == 1
        assert parsed["summary"]["total"] == 1

    def test_report_to_dict(self):
        """Report converts to dict correctly."""
        metadata = SelfTestReportMetadata(
            run_id="test",
            timestamp=datetime.now(timezone.utc).isoformat(),
            hostname="test",
            platform="linux",
            git_branch="main",
            git_commit="abc123",
            user="test",
            mode="strict",
        )
        summary = SelfTestSummary(
            passed=0,
            failed=0,
            skipped=0,
            total=0,
            critical_passed=0,
            critical_failed=0,
            warning_passed=0,
            warning_failed=0,
            info_passed=0,
            info_failed=0,
            category_security_passed=0,
            category_security_failed=0,
            category_performance_passed=0,
            category_performance_failed=0,
            category_correctness_passed=0,
            category_correctness_failed=0,
            category_governance_passed=0,
            category_governance_failed=0,
            total_duration_ms=0,
        )
        report = SelfTestReport(metadata=metadata, results=[], summary=summary)
        report_dict = report.to_dict()
        assert "metadata" in report_dict
        assert "results" in report_dict
        assert "summary" in report_dict


class TestArtifactManager:
    """Test artifact manager."""

    def test_artifact_manager_init(self):
        """Initialize artifact manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(Path(tmpdir))
            assert mgr.run_id is not None
            assert isinstance(mgr.run_id, str)
            assert len(mgr.run_id) > 0

    def test_get_run_base(self):
        """Get RUN_BASE path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(Path(tmpdir))
            run_base = mgr.get_run_base()
            assert "swarm/runs" in str(run_base)
            assert mgr.run_id in str(run_base)

    def test_get_artifact_path(self):
        """Get artifact path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(Path(tmpdir))
            path = mgr.get_artifact_path("build", "selftest_report.json")
            assert "build" in str(path)
            assert "selftest_report.json" in str(path)

    def test_write_read_artifact_json(self):
        """Write and read JSON artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(Path(tmpdir))
            data = {"test": "data", "number": 42}
            path = mgr.write_artifact("build", "test.json", data)
            assert path.exists()
            read_data = mgr.read_artifact("build", "test.json")
            assert read_data == data

    def test_write_read_artifact_text(self):
        """Write and read text artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(Path(tmpdir))
            text = "Hello, world!"
            path = mgr.write_artifact("build", "test.txt", text)
            assert path.exists()
            read_text = mgr.read_artifact("build", "test.txt")
            assert read_text == text

    def test_ensure_artifact_dir(self):
        """Ensure artifact directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(Path(tmpdir))
            dir_path = mgr.ensure_artifact_dir("build")
            assert dir_path.exists()
            assert dir_path.is_dir()

    def test_read_nonexistent_artifact(self):
        """Read nonexistent artifact returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(Path(tmpdir))
            result = mgr.read_artifact("build", "nonexistent.json")
            assert result is None


class TestOverrideManager:
    """Test override manager."""

    def test_override_creation(self):
        """Create override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            override = mgr.create_override(
                step_id="test-step",
                reason="Testing",
                approver="tester",
                hours=24,
            )
            assert override.step_id == "test-step"
            assert override.status == "APPROVED"
            assert override.reason == "Testing"
            assert override.approver == "tester"

    def test_override_is_active(self):
        """Check override is active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            mgr.create_override("test-step", "Testing", "tester", 24)
            assert mgr.is_override_active("test-step")

    def test_override_expires(self):
        """Override expires correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            # Create override that expires in the past
            mgr.create_override("test-step", "Testing", "tester", -1)
            assert not mgr.is_override_active("test-step")

    def test_override_list(self):
        """List overrides."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            mgr.create_override("step1", "Reason1", "user1", 24)
            mgr.create_override("step2", "Reason2", "user2", 24)
            overrides = mgr.list_overrides()
            assert len(overrides) == 2

    def test_override_revoke(self):
        """Revoke override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            mgr.create_override("test-step", "Testing", "tester", 24)
            assert mgr.is_override_active("test-step")
            success = mgr.revoke_override("test-step")
            assert success
            assert not mgr.is_override_active("test-step")

    def test_override_revoke_nonexistent(self):
        """Revoke nonexistent override returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            success = mgr.revoke_override("nonexistent")
            assert not success

    def test_override_replaces_previous(self):
        """New override revokes previous override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            mgr.create_override("test-step", "Reason1", "user1", 24)
            mgr.create_override("test-step", "Reason2", "user2", 24)
            overrides = mgr.load_overrides()
            approved_count = sum(1 for o in overrides if o.status == "APPROVED")
            assert approved_count == 1

    def test_override_load_empty(self):
        """Load empty overrides file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            overrides = mgr.load_overrides()
            assert overrides == []

    def test_override_timestamps_iso_format(self):
        """Override timestamps are ISO format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            override = mgr.create_override("test-step", "Testing", "tester", 24)
            # Should be able to parse as ISO format
            created = datetime.fromisoformat(override.created_at)
            expires = datetime.fromisoformat(override.expires_at)
            assert created < expires


class TestSelfTestDoctor:
    """Test doctor diagnostics."""

    def test_doctor_diagnose(self):
        """Run doctor diagnostics."""
        doctor = SelfTestDoctor()
        results = doctor.diagnose()
        assert "harness" in results
        assert "service" in results
        assert "summary" in results
        assert "recommendations" in results
        assert results["summary"] in ["HEALTHY", "HARNESS_ISSUE", "SERVICE_ISSUE"]

    def test_doctor_harness_checks(self):
        """Doctor includes harness checks."""
        doctor = SelfTestDoctor()
        results = doctor.diagnose()
        assert "python_env" in results["harness"]
        assert "rust_toolchain" in results["harness"]
        assert "git_state" in results["harness"]

    def test_doctor_service_checks(self):
        """Doctor includes service checks."""
        doctor = SelfTestDoctor()
        results = doctor.diagnose()
        assert "python_syntax" in results["service"]
        assert "cargo_check" in results["service"]

    def test_doctor_check_values_valid(self):
        """Doctor check values are valid."""
        doctor = SelfTestDoctor()
        results = doctor.diagnose()
        valid_values = ["OK", "ERROR", "WARNING"]
        for _, check_status in results["harness"].items():
            assert check_status in valid_values
        for _, check_status in results["service"].items():
            assert check_status in valid_values


class TestArtifactManagerHelpers:
    """Test artifact manager helper functions."""

    def test_get_platform_name(self):
        """Get platform name."""
        platform = get_platform_name()
        assert platform in ["linux", "darwin", "win32"]

    def test_get_hostname(self):
        """Get hostname."""
        hostname = get_hostname()
        assert isinstance(hostname, str)
        assert len(hostname) > 0


class TestStepRegistry:
    """Test the global SELFTEST_STEPS registry."""

    def test_all_10_steps_exist(self):
        """All 10 steps defined."""
        assert len(SELFTEST_STEPS) == 10

    def test_step_ids_unique(self):
        """Step IDs are unique."""
        ids = [step.id for step in SELFTEST_STEPS]
        assert len(ids) == len(set(ids))

    def test_step_descriptions_not_empty(self):
        """All step descriptions are non-empty."""
        for step in SELFTEST_STEPS:
            assert step.description
            assert len(step.description) > 0

    def test_step_commands_not_empty(self):
        """All step commands are non-empty."""
        for step in SELFTEST_STEPS:
            assert step.command
            assert len(step.command) > 0

    def test_kernel_steps_count(self):
        """Verify KERNEL tier step count."""
        kernel_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.KERNEL]
        assert len(kernel_steps) == 1  # Only core-checks

    def test_governance_steps_count(self):
        """Verify GOVERNANCE tier step count."""
        governance_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.GOVERNANCE]
        assert len(governance_steps) == 7  # 7 governance steps

    def test_optional_steps_count(self):
        """Verify OPTIONAL tier step count."""
        optional_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.OPTIONAL]
        assert len(optional_steps) == 2  # 2 optional steps

    def test_steps_in_order_function(self):
        """get_steps_in_order() works correctly."""
        steps = get_steps_in_order()
        assert len(steps) == 10
        assert steps[0].id == "core-checks"

    def test_steps_in_order_until_id(self):
        """get_steps_in_order() filters by until_id."""
        steps = get_steps_in_order(until_id="devex-contract")
        assert len(steps) == 7
        assert steps[-1].id == "devex-contract"

    def test_steps_in_order_filter_tier(self):
        """get_steps_in_order() filters by tier."""
        steps = get_steps_in_order(filter_tier=SelfTestTier.KERNEL)
        assert len(steps) == 1
        assert steps[0].id == "core-checks"

    def test_get_step_by_id(self):
        """get_step_by_id() retrieves steps."""
        step = get_step_by_id("core-checks")
        assert step is not None
        assert step.id == "core-checks"

    def test_get_step_by_id_nonexistent(self):
        """get_step_by_id() returns None for nonexistent step."""
        step = get_step_by_id("nonexistent-step")
        assert step is None

    def test_steps_have_valid_dependencies(self):
        """All step dependencies exist."""
        all_ids = {step.id for step in SELFTEST_STEPS}
        for step in SELFTEST_STEPS:
            if step.dependencies:
                for dep_id in step.dependencies:
                    assert dep_id in all_ids


class TestIntegration:
    """Integration tests across components."""

    def test_artifact_manager_with_report(self):
        """ArtifactManager can store and retrieve report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(Path(tmpdir))
            metadata = SelfTestReportMetadata(
                run_id="integration-test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                hostname="test",
                platform="linux",
                git_branch="main",
                git_commit="abc123",
                user="test",
                mode="strict",
            )
            summary = SelfTestSummary(
                passed=1,
                failed=0,
                skipped=0,
                total=1,
                critical_passed=1,
                critical_failed=0,
                warning_passed=0,
                warning_failed=0,
                info_passed=0,
                info_failed=0,
                category_security_passed=0,
                category_security_failed=0,
                category_performance_passed=0,
                category_performance_failed=0,
                category_correctness_passed=1,
                category_correctness_failed=0,
                category_governance_passed=0,
                category_governance_failed=0,
                total_duration_ms=1000,
            )
            report = SelfTestReport(metadata=metadata, results=[], summary=summary)
            report_dict = report.to_dict()
            mgr.write_artifact("build", "selftest_report.json", report_dict)
            retrieved = mgr.read_artifact("build", "selftest_report.json")
            assert retrieved == report_dict

    def test_override_manager_with_steps(self):
        """OverrideManager works with actual steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "overrides.json"
            mgr = OverrideManager(config_file)
            # Create override for first actual step
            first_step = SELFTEST_STEPS[0]
            mgr.create_override(first_step.id, "Testing", "tester", 24)
            assert mgr.is_override_active(first_step.id)

    def test_step_execution_sequence(self):
        """Steps respect dependency order."""
        for step in SELFTEST_STEPS:
            if step.dependencies:
                # Find indices
                dep_indices = []
                for dep_id in step.dependencies:
                    for i, s in enumerate(SELFTEST_STEPS):
                        if s.id == dep_id:
                            dep_indices.append(i)
                # All dependencies should come before this step
                current_index = None
                for i, s in enumerate(SELFTEST_STEPS):
                    if s.id == step.id:
                        current_index = i
                        break
                for dep_index in dep_indices:
                    assert dep_index < current_index


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
