"""Tests for the selftest runner."""

import pytest

from selftest_core import (
    Category,
    SelfTestRunner,
    Severity,
    Step,
    StepResult,
    Tier,
)


class TestStep:
    """Tests for Step dataclass."""

    def test_step_creation(self):
        """Test basic step creation."""
        step = Step(
            id="test-step",
            tier=Tier.KERNEL,
            command="echo hello",
            description="Test step",
        )
        assert step.id == "test-step"
        assert step.tier == Tier.KERNEL
        assert step.command == "echo hello"
        assert step.description == "Test step"

    def test_step_defaults(self):
        """Test default values."""
        step = Step(
            id="test",
            tier=Tier.KERNEL,
            command="true",
        )
        assert step.description == ""
        assert step.severity == Severity.WARNING
        assert step.category == Category.CORRECTNESS
        assert step.timeout == 60
        assert step.dependencies == []
        assert step.allow_fail_in_degraded is False

    def test_step_requires_id(self):
        """Test that id is required."""
        with pytest.raises(ValueError, match="id is required"):
            Step(id="", tier=Tier.KERNEL, command="true")

    def test_step_requires_command(self):
        """Test that command is required."""
        with pytest.raises(ValueError, match="command is required"):
            Step(id="test", tier=Tier.KERNEL, command="")

    def test_step_requires_tier_enum(self):
        """Test that tier must be Tier enum."""
        with pytest.raises(ValueError, match="tier must be a Tier enum"):
            Step(id="test", tier="kernel", command="true")  # type: ignore


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = StepResult(
            step_id="test",
            status="PASS",
            duration_ms=100,
            output="hello",
            error="",
            exit_code=0,
            tier="kernel",
            severity="critical",
            category="correctness",
        )
        d = result.to_dict()
        assert d["step_id"] == "test"
        assert d["status"] == "PASS"
        assert d["duration_ms"] == 100
        assert d["exit_code"] == 0


class TestSelfTestRunner:
    """Tests for SelfTestRunner."""

    def test_run_passing_step(self):
        """Test running a passing step."""
        steps = [
            Step(id="pass", tier=Tier.KERNEL, command="true"),
        ]
        runner = SelfTestRunner(steps)
        result = runner.run()

        assert result["status"] == "PASS"
        assert result["passed"] == 1
        assert result["failed"] == 0
        assert result["total"] == 1

    def test_run_failing_step(self):
        """Test running a failing step."""
        steps = [
            Step(id="fail", tier=Tier.KERNEL, command="false"),
        ]
        runner = SelfTestRunner(steps)
        result = runner.run()

        assert result["status"] == "FAIL"
        assert result["passed"] == 0
        assert result["failed"] == 1
        assert "fail" in result["failed_steps"]

    def test_kernel_only_mode(self):
        """Test kernel-only mode filters steps."""
        steps = [
            Step(id="kernel", tier=Tier.KERNEL, command="true"),
            Step(id="gov", tier=Tier.GOVERNANCE, command="true"),
            Step(id="opt", tier=Tier.OPTIONAL, command="true"),
        ]
        runner = SelfTestRunner(steps, mode="kernel-only")
        result = runner.run()

        assert result["total"] == 1
        assert result["passed"] == 1
        step_ids = [r["step_id"] for r in result["results"]]
        assert "kernel" in step_ids
        assert "gov" not in step_ids
        assert "opt" not in step_ids

    def test_degraded_mode_governance_warning(self):
        """Test degraded mode treats governance failures as warnings."""
        steps = [
            Step(id="kernel", tier=Tier.KERNEL, command="true"),
            Step(id="gov", tier=Tier.GOVERNANCE, command="false"),
        ]
        runner = SelfTestRunner(steps, mode="degraded")
        result = runner.run()

        # Should pass because governance failure doesn't block in degraded mode
        assert result["status"] == "PASS"
        assert result["kernel_ok"] is True
        assert result["governance_ok"] is False

    def test_strict_mode_governance_blocks(self):
        """Test strict mode blocks on governance failure."""
        steps = [
            Step(id="kernel", tier=Tier.KERNEL, command="true"),
            Step(id="gov", tier=Tier.GOVERNANCE, command="false"),
        ]
        runner = SelfTestRunner(steps, mode="strict")
        result = runner.run()

        assert result["status"] == "FAIL"
        assert "gov" in result["failed_steps"]

    def test_optional_never_blocks(self):
        """Test optional failures never block."""
        steps = [
            Step(id="kernel", tier=Tier.KERNEL, command="true"),
            Step(id="opt", tier=Tier.OPTIONAL, command="false"),
        ]
        runner = SelfTestRunner(steps, mode="strict")
        result = runner.run()

        # Should pass because optional failures don't block
        assert result["status"] == "PASS"
        assert result["optional_ok"] is False

    def test_dependency_skip(self):
        """Test that steps with failed dependencies are skipped."""
        steps = [
            Step(id="first", tier=Tier.KERNEL, command="false"),
            Step(id="second", tier=Tier.KERNEL, command="true", dependencies=["first"]),
        ]
        runner = SelfTestRunner(steps, mode="degraded")
        result = runner.run()

        # Second step should be skipped due to dependency
        assert result["skipped"] == 1
        second_result = next(r for r in result["results"] if r["step_id"] == "second")
        assert second_result["status"] == "SKIP"

    def test_plan_returns_steps(self):
        """Test plan method returns step information."""
        steps = [
            Step(
                id="lint", tier=Tier.KERNEL, command="ruff check .", description="Lint"
            ),
            Step(id="test", tier=Tier.KERNEL, command="pytest", description="Test"),
        ]
        runner = SelfTestRunner(steps)
        plan = runner.plan()

        assert plan["version"] == "1.0"
        assert len(plan["steps"]) == 2
        assert plan["summary"]["total"] == 2
        assert plan["summary"]["by_tier"]["kernel"] == 2

    def test_callbacks_invoked(self):
        """Test that step callbacks are invoked."""
        started = []
        completed = []

        def on_start(step):
            started.append(step.id)

        def on_complete(step, result):
            completed.append((step.id, result.status))

        steps = [
            Step(id="test", tier=Tier.KERNEL, command="true"),
        ]
        runner = SelfTestRunner(
            steps,
            on_step_start=on_start,
            on_step_complete=on_complete,
        )
        runner.run()

        assert "test" in started
        assert ("test", "PASS") in completed

    def test_step_timeout(self):
        """Test step timeout handling."""
        steps = [
            Step(id="slow", tier=Tier.KERNEL, command="sleep 10", timeout=1),
        ]
        runner = SelfTestRunner(steps)
        result = runner.run()

        assert result["status"] == "FAIL"
        slow_result = result["results"][0]
        assert slow_result["status"] == "FAIL"
        assert "Timeout" in slow_result["error"]

    def test_severity_breakdown(self):
        """Test severity breakdown in results."""
        steps = [
            Step(
                id="crit", tier=Tier.KERNEL, command="true", severity=Severity.CRITICAL
            ),
            Step(
                id="warn",
                tier=Tier.GOVERNANCE,
                command="true",
                severity=Severity.WARNING,
            ),
            Step(id="info", tier=Tier.OPTIONAL, command="true", severity=Severity.INFO),
        ]
        runner = SelfTestRunner(steps)
        result = runner.run()

        by_sev = result["by_severity"]
        assert by_sev["critical"]["passed"] == 1
        assert by_sev["warning"]["passed"] == 1
        assert by_sev["info"]["passed"] == 1

    def test_category_breakdown(self):
        """Test category breakdown in results."""
        steps = [
            Step(
                id="sec", tier=Tier.KERNEL, command="true", category=Category.SECURITY
            ),
            Step(
                id="perf",
                tier=Tier.KERNEL,
                command="true",
                category=Category.PERFORMANCE,
            ),
            Step(
                id="correct",
                tier=Tier.KERNEL,
                command="true",
                category=Category.CORRECTNESS,
            ),
        ]
        runner = SelfTestRunner(steps)
        result = runner.run()

        by_cat = result["by_category"]
        assert by_cat["security"]["passed"] == 1
        assert by_cat["performance"]["passed"] == 1
        assert by_cat["correctness"]["passed"] == 1


class TestTierEnum:
    """Tests for Tier enum."""

    def test_tier_values(self):
        """Test tier enum values."""
        assert Tier.KERNEL.value == "kernel"
        assert Tier.GOVERNANCE.value == "governance"
        assert Tier.OPTIONAL.value == "optional"


class TestSeverityEnum:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"


class TestCategoryEnum:
    """Tests for Category enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert Category.SECURITY.value == "security"
        assert Category.PERFORMANCE.value == "performance"
        assert Category.CORRECTNESS.value == "correctness"
        assert Category.GOVERNANCE.value == "governance"
