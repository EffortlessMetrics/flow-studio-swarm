"""Tests for the doctor diagnostic tool."""

from selftest_core.doctor import (
    DiagnosticCheck,
    SelfTestDoctor,
    make_command_check,
    make_env_var_check,
    make_python_package_check,
)


class TestSelfTestDoctor:
    """Tests for SelfTestDoctor class."""

    def test_basic_diagnosis(self):
        """Test basic diagnosis runs."""
        doctor = SelfTestDoctor()
        diagnosis = doctor.diagnose()

        assert "harness" in diagnosis
        assert "service" in diagnosis
        assert "summary" in diagnosis
        assert "recommendations" in diagnosis

    def test_summary_values(self):
        """Test summary has valid values."""
        doctor = SelfTestDoctor()
        diagnosis = doctor.diagnose()

        assert diagnosis["summary"] in ("HEALTHY", "HARNESS_ISSUE", "SERVICE_ISSUE")

    def test_healthy_with_all_ok(self):
        """Test HEALTHY summary when all checks pass."""
        checks = [
            DiagnosticCheck(
                name="always_ok",
                category="harness",
                check_fn=lambda: ("OK", None),
            ),
            DiagnosticCheck(
                name="service_ok",
                category="service",
                check_fn=lambda: ("OK", None),
            ),
        ]
        doctor = SelfTestDoctor(checks=checks)
        diagnosis = doctor.diagnose()

        assert diagnosis["summary"] == "HEALTHY"

    def test_harness_issue_on_harness_failure(self):
        """Test HARNESS_ISSUE when harness check fails."""
        checks = [
            DiagnosticCheck(
                name="harness_fail",
                category="harness",
                check_fn=lambda: ("ERROR", "Fix harness"),
            ),
        ]
        doctor = SelfTestDoctor(checks=checks)
        diagnosis = doctor.diagnose()

        assert diagnosis["summary"] == "HARNESS_ISSUE"
        assert "Fix harness" in diagnosis["recommendations"]

    def test_service_issue_on_service_failure(self):
        """Test SERVICE_ISSUE when service check fails."""
        checks = [
            DiagnosticCheck(
                name="harness_ok",
                category="harness",
                check_fn=lambda: ("OK", None),
            ),
            DiagnosticCheck(
                name="service_fail",
                category="service",
                check_fn=lambda: ("ERROR", "Fix service"),
            ),
        ]
        doctor = SelfTestDoctor(checks=checks)
        diagnosis = doctor.diagnose()

        assert diagnosis["summary"] == "SERVICE_ISSUE"
        assert "Fix service" in diagnosis["recommendations"]

    def test_warning_allows_healthy(self):
        """Test that WARNING status still allows HEALTHY summary."""
        checks = [
            DiagnosticCheck(
                name="warning_check",
                category="harness",
                check_fn=lambda: ("WARNING", "Consider fixing"),
            ),
        ]
        doctor = SelfTestDoctor(checks=checks)
        diagnosis = doctor.diagnose()

        assert diagnosis["summary"] == "HEALTHY"

    def test_add_check(self):
        """Test adding custom check."""
        doctor = SelfTestDoctor(checks=[])
        doctor.add_check(
            DiagnosticCheck(
                name="custom",
                category="harness",
                check_fn=lambda: ("OK", None),
            )
        )
        diagnosis = doctor.diagnose()

        assert "custom" in diagnosis["harness"]


class TestMakeCommandCheck:
    """Tests for make_command_check helper."""

    def test_passing_command(self):
        """Test check with passing command."""
        check = make_command_check(
            name="pass",
            command="true",
            category="harness",
        )
        status, rec = check.check_fn()
        assert status == "OK"
        assert rec is None

    def test_failing_command(self):
        """Test check with failing command."""
        check = make_command_check(
            name="fail",
            command="false",
            category="harness",
            error_message="Command failed",
        )
        status, rec = check.check_fn()
        assert status == "ERROR"
        assert rec == "Command failed"

    def test_timeout(self):
        """Test check with timeout."""
        check = make_command_check(
            name="slow",
            command="sleep 10",
            category="harness",
            timeout=1,
        )
        status, rec = check.check_fn()
        assert status == "ERROR"
        assert "timed out" in rec


class TestMakePythonPackageCheck:
    """Tests for make_python_package_check helper."""

    def test_existing_package(self):
        """Test check for existing package."""
        check = make_python_package_check("sys")
        status, rec = check.check_fn()
        assert status == "OK"

    def test_missing_package(self):
        """Test check for missing package."""
        check = make_python_package_check("nonexistent_package_xyz")
        status, rec = check.check_fn()
        assert status == "ERROR"
        assert "Install" in rec


class TestMakeEnvVarCheck:
    """Tests for make_env_var_check helper."""

    def test_existing_var(self):
        """Test check for existing env var."""
        import os

        os.environ["TEST_SELFTEST_VAR"] = "value"
        try:
            check = make_env_var_check("TEST_SELFTEST_VAR")
            status, rec = check.check_fn()
            assert status == "OK"
        finally:
            del os.environ["TEST_SELFTEST_VAR"]

    def test_missing_required_var(self):
        """Test check for missing required var."""
        import os

        if "NONEXISTENT_VAR_XYZ" in os.environ:
            del os.environ["NONEXISTENT_VAR_XYZ"]

        check = make_env_var_check("NONEXISTENT_VAR_XYZ", required=True)
        status, rec = check.check_fn()
        assert status == "ERROR"

    def test_missing_optional_var(self):
        """Test check for missing optional var."""
        import os

        if "NONEXISTENT_VAR_XYZ" in os.environ:
            del os.environ["NONEXISTENT_VAR_XYZ"]

        check = make_env_var_check("NONEXISTENT_VAR_XYZ", required=False)
        status, rec = check.check_fn()
        assert status == "WARNING"


class TestDiagnosticCheck:
    """Tests for DiagnosticCheck dataclass."""

    def test_basic_check(self):
        """Test basic check creation."""
        check = DiagnosticCheck(
            name="test",
            category="harness",
            check_fn=lambda: ("OK", None),
        )
        assert check.name == "test"
        assert check.category == "harness"
        assert check.required is True

    def test_check_invocation(self):
        """Test check function is invoked correctly."""
        check = DiagnosticCheck(
            name="test",
            category="service",
            check_fn=lambda: ("ERROR", "Fix it"),
        )
        status, rec = check.check_fn()
        assert status == "ERROR"
        assert rec == "Fix it"
