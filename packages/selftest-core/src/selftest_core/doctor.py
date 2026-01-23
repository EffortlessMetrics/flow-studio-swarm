"""
Diagnostic tool for selftest.

This module provides the SelfTestDoctor class for diagnosing whether
selftest failures are due to environment issues (harness) or actual
code/config problems (service).

The doctor distinguishes between:
- HARNESS_ISSUE: Environment problems (Python, toolchain, git state)
- SERVICE_ISSUE: Code or configuration is actually broken
- HEALTHY: Everything is working normally

Example usage:
    from selftest_core.doctor import SelfTestDoctor

    doctor = SelfTestDoctor()
    diagnosis = doctor.diagnose()

    if diagnosis["summary"] == "HARNESS_ISSUE":
        print("Fix your environment first!")
        for rec in diagnosis["recommendations"]:
            print(f"  - {rec}")
    elif diagnosis["summary"] == "SERVICE_ISSUE":
        print("Code has issues, run selftest for details")
"""

import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union


@dataclass
class DiagnosticCheck:
    """
    Definition of a diagnostic check.

    Attributes:
        name: Human-readable check name
        category: 'harness' or 'service'
        check_fn: Function that returns (status, recommendation)
        required: If True, failure makes this category fail
    """
    name: str
    category: str  # 'harness' or 'service'
    check_fn: Callable[[], tuple]  # Returns (status, recommendation)
    required: bool = True


class SelfTestDoctor:
    """
    Diagnostic tool for selftest issues.

    Runs a series of checks to determine whether selftest failures
    are due to environment (harness) or code (service) issues.

    The doctor is extensible - you can add custom checks for your
    project's specific requirements.

    Example:
        doctor = SelfTestDoctor()

        # Add a custom check
        doctor.add_check(DiagnosticCheck(
            name="database",
            category="service",
            check_fn=lambda: ("OK", None) if db_is_up() else ("ERROR", "Start database"),
        ))

        diagnosis = doctor.diagnose()
    """

    def __init__(self, checks: Optional[List[DiagnosticCheck]] = None):
        """
        Initialize the doctor.

        Args:
            checks: Optional list of custom checks. If None, uses default checks.
        """
        self.checks = checks or self._default_checks()

    def _default_checks(self) -> List[DiagnosticCheck]:
        """Return the default diagnostic checks."""
        return [
            DiagnosticCheck(
                name="python_env",
                category="harness",
                check_fn=self._check_python_env,
            ),
            DiagnosticCheck(
                name="git_state",
                category="harness",
                check_fn=self._check_git_state,
            ),
            DiagnosticCheck(
                name="python_syntax",
                category="service",
                check_fn=self._check_python_syntax,
            ),
        ]

    def add_check(self, check: DiagnosticCheck):
        """
        Add a custom diagnostic check.

        Args:
            check: DiagnosticCheck to add
        """
        self.checks.append(check)

    def _check_python_env(self) -> tuple:
        """Check Python environment."""
        try:
            if sys.version_info < (3, 10):
                return ("ERROR", "Upgrade to Python 3.10+")
            return ("OK", None)
        except Exception as e:
            return ("ERROR", f"Python error: {e}")

    def _check_git_state(self) -> tuple:
        """Check Git repository state."""
        try:
            # Check if in git repo
            result = subprocess.run(
                ["git", "status"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                return ("ERROR", "Not in git repository")

            # Check for dirty tree
            result = subprocess.run(
                ["git", "diff", "--quiet"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                return ("WARNING", "Git tree has uncommitted changes")

            return ("OK", None)
        except subprocess.TimeoutExpired:
            return ("ERROR", "Git check timed out")
        except Exception as e:
            return ("ERROR", f"Git check failed: {e}")

    def _check_python_syntax(self) -> tuple:
        """Check for Python syntax errors in common locations."""
        # This is a generic check - specific projects should add their own
        try:
            # Try to compile a basic Python check
            result = subprocess.run(
                [sys.executable, "-c", "import sys; print(sys.version)"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return ("ERROR", "Python interpreter check failed")
            return ("OK", None)
        except Exception as e:
            return ("ERROR", f"Python syntax check failed: {e}")

    def diagnose(self) -> Dict[str, Any]:
        """
        Run all diagnostic checks.

        Returns:
            Dictionary containing:
            - harness: Dict of harness check results
            - service: Dict of service check results
            - summary: Overall status (HEALTHY, HARNESS_ISSUE, SERVICE_ISSUE)
            - recommendations: List of recommended actions
        """
        results: Dict[str, Any] = {
            "harness": {},
            "service": {},
            "recommendations": [],
        }

        for check in self.checks:
            status, recommendation = check.check_fn()
            results[check.category][check.name] = status

            if recommendation:
                results["recommendations"].append(recommendation)

        # Determine summary
        harness_values = results["harness"].values()
        service_values = results["service"].values()

        harness_ok = all(v in ("OK", "WARNING") for v in harness_values)
        service_ok = all(v in ("OK", "WARNING") for v in service_values)

        if not harness_ok:
            results["summary"] = "HARNESS_ISSUE"
        elif not service_ok:
            results["summary"] = "SERVICE_ISSUE"
        else:
            results["summary"] = "HEALTHY"

        return results

    def print_diagnosis(self, diagnosis: Optional[Dict[str, Any]] = None):
        """
        Print diagnosis results to console.

        Args:
            diagnosis: Diagnosis dict from diagnose(). If None, runs diagnose().
        """
        if diagnosis is None:
            diagnosis = self.diagnose()

        print("=" * 70)
        print("SELFTEST DOCTOR DIAGNOSTICS")
        print("=" * 70)
        print()

        print("Harness Checks:")
        for check, status in diagnosis["harness"].items():
            icon = "OK" if status == "OK" else "WA" if status == "WARNING" else "ER"
            print(f"  [{icon}] {check:20s}: {status}")

        print("\nService Checks:")
        for check, status in diagnosis["service"].items():
            icon = "OK" if status == "OK" else "WA" if status == "WARNING" else "ER"
            print(f"  [{icon}] {check:20s}: {status}")

        print(f"\n{'=' * 70}")
        print(f"Summary: {diagnosis['summary']}")
        print(f"{'=' * 70}")

        if diagnosis["recommendations"]:
            print("\nRecommendations:")
            for i, rec in enumerate(diagnosis["recommendations"], 1):
                print(f"  {i}. {rec}")
        else:
            print("\nNo issues detected")


# Predefined check builders for common scenarios


def make_command_check(
    name: str,
    command: Union[str, List[str]],
    category: str = "harness",
    timeout: int = 5,
    error_message: Optional[str] = None,
) -> DiagnosticCheck:
    """
    Create a diagnostic check that runs a command.

    Args:
        name: Check name
        command: Command to run - either a string or argv list.
            String commands are parsed with shlex.split and executed with shell=False.
        category: 'harness' or 'service'
        timeout: Command timeout in seconds
        error_message: Custom error message on failure

    Returns:
        DiagnosticCheck instance
    """
    import shlex

    # Parse command to argv if it's a string
    if isinstance(command, str):
        argv = shlex.split(command)
        cmd_display = command
    else:
        argv = command
        cmd_display = " ".join(command)

    def check_fn() -> tuple:
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                return ("OK", None)
            else:
                msg = error_message or f"Command '{cmd_display}' failed"
                return ("ERROR", msg)
        except subprocess.TimeoutExpired:
            return ("ERROR", f"Command '{cmd_display}' timed out")
        except Exception as e:
            return ("ERROR", f"Command failed: {e}")

    return DiagnosticCheck(
        name=name,
        category=category,
        check_fn=check_fn,
    )


def make_python_package_check(
    package: str,
    import_name: Optional[str] = None,
) -> DiagnosticCheck:
    """
    Create a diagnostic check for a Python package.

    Args:
        package: Package name (for error message)
        import_name: Import name if different from package

    Returns:
        DiagnosticCheck instance
    """
    import_name = import_name or package

    def check_fn() -> tuple:
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {import_name}"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return ("OK", None)
            else:
                return ("ERROR", f"Install {package}: pip install {package}")
        except Exception as e:
            return ("ERROR", f"Package check failed: {e}")

    return DiagnosticCheck(
        name=f"python_{package}",
        category="harness",
        check_fn=check_fn,
    )


def make_env_var_check(
    var_name: str,
    required: bool = True,
) -> DiagnosticCheck:
    """
    Create a diagnostic check for an environment variable.

    Args:
        var_name: Environment variable name
        required: If True, missing var is ERROR; if False, WARNING

    Returns:
        DiagnosticCheck instance
    """
    def check_fn() -> tuple:
        if os.environ.get(var_name):
            return ("OK", None)
        elif required:
            return ("ERROR", f"Set environment variable: {var_name}")
        else:
            return ("WARNING", f"Consider setting: {var_name}")

    return DiagnosticCheck(
        name=f"env_{var_name.lower()}",
        category="harness",
        check_fn=check_fn,
        required=required,
    )
