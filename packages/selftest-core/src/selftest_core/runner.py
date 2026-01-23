"""
Selftest runner - core execution engine.

This module provides the core execution engine for running selftest steps
with tier-aware execution, degraded mode support, and detailed reporting.

The runner implements a three-tier governance model:
- KERNEL: Must always pass; blocks on failure
- GOVERNANCE: Should pass; can warn in degraded mode
- OPTIONAL: Nice-to-have; failures are informational

Example usage:
    from selftest_core import SelfTestRunner, Step, Tier

    steps = [
        Step(
            id="lint",
            tier=Tier.KERNEL,
            command="ruff check .",
            description="Python linting",
        ),
        Step(
            id="test",
            tier=Tier.KERNEL,
            command="pytest tests/",
            description="Unit tests",
        ),
    ]

    runner = SelfTestRunner(steps, mode="strict")
    result = runner.run()
    print(f"Status: {result['status']}")
"""

import re
import shlex
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Shell metacharacters that indicate potential command injection
# These require explicit opt-in if the user truly needs shell features
SHELL_METACHAR_PATTERN = re.compile(r"[|;&$`><]|\$\(")


def parse_command(command: str | list[str]) -> list[str]:
    """
    Parse a command into an argv list for shell=False execution.

    Args:
        command: Either a string command or pre-parsed argv list

    Returns:
        List of command arguments suitable for subprocess with shell=False

    Raises:
        ValueError: If command contains shell metacharacters
    """
    if isinstance(command, list):
        return command

    # Check for shell metacharacters that could indicate injection
    if SHELL_METACHAR_PATTERN.search(command):
        raise ValueError(
            f"Command contains shell metacharacters which are not supported: "
            f"{command!r}. Use an argv list instead or redesign the step to "
            "avoid shell features."
        )

    return shlex.split(command)


class Tier(Enum):
    """
    Selftest tier indicating criticality and failure behavior.

    Tiers control execution flow and failure handling:
    - KERNEL: Critical checks that must pass; failure blocks workflow
    - GOVERNANCE: Important checks that should pass; can be warnings in degraded mode
    - OPTIONAL: Nice-to-have checks; failures are purely informational
    """

    KERNEL = "kernel"
    GOVERNANCE = "governance"
    OPTIONAL = "optional"


class Severity(Enum):
    """
    Severity level of a selftest step.

    Severity provides additional classification beyond tiers:
    - CRITICAL: Must be addressed immediately
    - WARNING: Should be addressed soon
    - INFO: Informational only
    """

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Category(Enum):
    """
    Category of a selftest step.

    Categories help organize and filter steps by concern:
    - SECURITY: Security-related checks
    - PERFORMANCE: Performance-related checks
    - CORRECTNESS: Code correctness checks (lint, type, test)
    - GOVERNANCE: Process and policy checks
    """

    SECURITY = "security"
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    GOVERNANCE = "governance"


@dataclass
class Step:
    """
    Represents one selftest step.

    A step is the atomic unit of testing. It has an ID, tier, command to run,
    and optional metadata for filtering and reporting.

    Attributes:
        id: Unique identifier (e.g., 'core-checks')
        tier: Tier classification (KERNEL, GOVERNANCE, OPTIONAL)
        command: Command to execute - either a string or argv list.
            String commands are parsed with shlex.split and executed with shell=False.
            Shell metacharacters (|, &, ;, $, `, >, <) are rejected for security.
        description: Human-readable description of what this step checks
        severity: Severity level (CRITICAL, WARNING, INFO)
        category: Category for filtering (SECURITY, PERFORMANCE, etc.)
        timeout: Maximum execution time in seconds (default: 60)
        dependencies: List of step IDs that must pass before this step runs
        allow_fail_in_degraded: If True, failures become warnings in degraded mode
    """

    id: str
    tier: Tier
    command: str | list[str]
    description: str = ""
    severity: Severity = Severity.WARNING
    category: Category = Category.CORRECTNESS
    timeout: int = 60
    dependencies: list[str] = field(default_factory=list)
    allow_fail_in_degraded: bool = False

    def __post_init__(self):
        """Validate step definition."""
        if not self.id:
            raise ValueError("Step id is required")
        if not self.command:
            raise ValueError("Step command is required")
        if not isinstance(self.tier, Tier):
            raise ValueError(f"tier must be a Tier enum, got {type(self.tier)}")


@dataclass
class StepResult:
    """
    Result of running a single selftest step.

    Contains execution details including status, timing, and output.

    Attributes:
        step_id: ID of the step that was executed
        status: Execution status (PASS, FAIL, SKIP)
        duration_ms: Execution time in milliseconds
        output: Standard output from the command
        error: Standard error or error message
        exit_code: Process exit code (-1 if not applicable)
        tier: Tier of the step (copied for convenience)
        severity: Severity of the step (copied for convenience)
        category: Category of the step (copied for convenience)
    """

    step_id: str
    status: str  # PASS, FAIL, SKIP
    duration_ms: int
    output: str = ""
    error: str = ""
    exit_code: int = -1
    tier: str = ""
    severity: str = ""
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "step_id": self.step_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "tier": self.tier,
            "severity": self.severity,
            "category": self.category,
        }


class SelfTestRunner:
    """
    Core selftest execution engine.

    The runner executes steps in order, respecting dependencies and tier
    constraints. It supports multiple execution modes:

    - strict: KERNEL and GOVERNANCE failures block (default)
    - degraded: Only KERNEL failures block; GOVERNANCE/OPTIONAL are warnings
    - kernel-only: Run only KERNEL tier steps

    Example:
        runner = SelfTestRunner(steps, mode="strict")
        result = runner.run()

        if result["status"] == "PASS":
            print("All checks passed!")
        else:
            for failed in result["failed_steps"]:
                print(f"Failed: {failed}")
    """

    def __init__(
        self,
        steps: list[Step],
        mode: str = "strict",
        verbose: bool = False,
        on_step_start: Callable[[Step], None] | None = None,
        on_step_complete: Callable[[Step, StepResult], None] | None = None,
    ):
        """
        Initialize the runner.

        Args:
            steps: List of Step objects to execute
            mode: Execution mode ('strict', 'degraded', or 'kernel-only')
            verbose: If True, print detailed output during execution
            on_step_start: Optional callback invoked before each step
            on_step_complete: Optional callback invoked after each step
        """
        self.steps = steps
        self.mode = mode
        self.verbose = verbose
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete
        self.results: list[StepResult] = []
        self._step_results: dict[str, StepResult] = {}

    def _filter_steps(self) -> list[Step]:
        """Filter steps based on mode."""
        if self.mode == "kernel-only":
            return [s for s in self.steps if s.tier == Tier.KERNEL]
        return self.steps

    def _check_dependencies(self, step: Step) -> bool:
        """
        Check if all dependencies for a step have passed.

        Returns:
            True if all dependencies passed, False otherwise
        """
        for dep_id in step.dependencies:
            dep_result = self._step_results.get(dep_id)
            if dep_result is None or dep_result.status != "PASS":
                return False
        return True

    def run_step(self, step: Step) -> StepResult:
        """
        Execute a single step.

        Args:
            step: The Step to execute

        Returns:
            StepResult with execution details
        """
        # Invoke start callback
        if self.on_step_start:
            self.on_step_start(step)

        # Check dependencies
        if step.dependencies and not self._check_dependencies(step):
            result = StepResult(
                step_id=step.id,
                status="SKIP",
                duration_ms=0,
                output="",
                error="Dependency not satisfied",
                exit_code=-1,
                tier=step.tier.value,
                severity=step.severity.value,
                category=step.category.value,
            )
            if self.on_step_complete:
                self.on_step_complete(step, result)
            return result

        # Execute the command
        start = time.time()
        try:
            # Parse command to argv list (rejects shell metacharacters)
            argv = parse_command(step.command)
            proc = subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=step.timeout,
            )
            status = "PASS" if proc.returncode == 0 else "FAIL"
            output = proc.stdout
            error = proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            status = "FAIL"
            output = ""
            error = f"Timeout after {step.timeout}s"
            exit_code = -1
        except ValueError as e:
            # parse_command raised due to shell metacharacters
            status = "FAIL"
            output = ""
            error = str(e)
            exit_code = -1
        except Exception as e:
            status = "FAIL"
            output = ""
            error = str(e)
            exit_code = -1

        duration = int((time.time() - start) * 1000)
        result = StepResult(
            step_id=step.id,
            status=status,
            duration_ms=duration,
            output=output,
            error=error,
            exit_code=exit_code,
            tier=step.tier.value,
            severity=step.severity.value,
            category=step.category.value,
        )

        # Invoke completion callback
        if self.on_step_complete:
            self.on_step_complete(step, result)

        return result

    def run(self) -> dict[str, Any]:
        """
        Run all steps and return summary.

        Executes steps in order, respecting the configured mode and
        dependency constraints.

        Returns:
            Dictionary containing:
            - status: Overall status (PASS or FAIL)
            - mode: Execution mode used
            - passed: Count of passed steps
            - failed: Count of failed steps
            - skipped: Count of skipped steps
            - total: Total step count
            - total_duration_ms: Total execution time
            - results: List of StepResult dictionaries
            - failed_steps: List of failed step IDs
            - kernel_ok: True if all KERNEL steps passed
            - governance_ok: True if all GOVERNANCE steps passed
        """
        self.results = []
        self._step_results = {}
        failed_steps: list[str] = []
        kernel_failed: list[str] = []
        governance_failed: list[str] = []
        optional_failed: list[str] = []

        steps = self._filter_steps()

        for step in steps:
            result = self.run_step(step)
            self.results.append(result)
            self._step_results[step.id] = result

            # Track failures by tier
            if result.status == "FAIL":
                if step.tier == Tier.KERNEL:
                    kernel_failed.append(step.id)
                    failed_steps.append(step.id)
                elif step.tier == Tier.GOVERNANCE:
                    governance_failed.append(step.id)
                    if self.mode == "strict":
                        failed_steps.append(step.id)
                elif step.tier == Tier.OPTIONAL:
                    optional_failed.append(step.id)
                    # Optional failures never block

                # In strict mode, stop on kernel failure
                if self.mode == "strict" and step.tier == Tier.KERNEL:
                    break

        return self._build_summary(
            failed_steps=failed_steps,
            kernel_failed=kernel_failed,
            governance_failed=governance_failed,
            optional_failed=optional_failed,
        )

    def _build_summary(
        self,
        failed_steps: list[str],
        kernel_failed: list[str],
        governance_failed: list[str],
        optional_failed: list[str],
    ) -> dict[str, Any]:
        """Build the run summary dictionary."""
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        skipped = sum(1 for r in self.results if r.status == "SKIP")
        total_duration = sum(r.duration_ms for r in self.results)

        # Determine overall status based on mode
        if self.mode == "degraded":
            # Only kernel failures matter
            overall_status = "FAIL" if kernel_failed else "PASS"
        else:
            # Strict mode: kernel and governance failures matter
            overall_status = "FAIL" if failed_steps else "PASS"

        # Build severity breakdown
        by_severity: dict[str, dict[str, int]] = {}
        for sev in Severity:
            sev_results = [r for r in self.results if r.severity == sev.value]
            by_severity[sev.value] = {
                "passed": sum(1 for r in sev_results if r.status == "PASS"),
                "failed": sum(1 for r in sev_results if r.status == "FAIL"),
                "total": len(sev_results),
            }

        # Build category breakdown
        by_category: dict[str, dict[str, int]] = {}
        for cat in Category:
            cat_results = [r for r in self.results if r.category == cat.value]
            by_category[cat.value] = {
                "passed": sum(1 for r in cat_results if r.status == "PASS"),
                "failed": sum(1 for r in cat_results if r.status == "FAIL"),
                "total": len(cat_results),
            }

        return {
            "status": overall_status,
            "mode": self.mode,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": len(self.results),
            "total_duration_ms": total_duration,
            "results": [r.to_dict() for r in self.results],
            "failed_steps": failed_steps,
            "kernel_ok": len(kernel_failed) == 0,
            "kernel_failed": kernel_failed,
            "governance_ok": len(governance_failed) == 0,
            "governance_failed": governance_failed,
            "optional_ok": len(optional_failed) == 0,
            "optional_failed": optional_failed,
            "by_severity": by_severity,
            "by_category": by_category,
        }

    def plan(self) -> dict[str, Any]:
        """
        Get the execution plan without running.

        Returns:
            Dictionary containing step plan and summary
        """
        steps = self._filter_steps()
        return {
            "version": "1.0",
            "mode": self.mode,
            "steps": [
                {
                    "id": step.id,
                    "tier": step.tier.value,
                    "severity": step.severity.value,
                    "category": step.category.value,
                    "description": step.description,
                    "command": step.command,
                    "dependencies": step.dependencies,
                    "timeout": step.timeout,
                }
                for step in steps
            ],
            "summary": {
                "total": len(steps),
                "by_tier": {
                    "kernel": sum(1 for s in steps if s.tier == Tier.KERNEL),
                    "governance": sum(1 for s in steps if s.tier == Tier.GOVERNANCE),
                    "optional": sum(1 for s in steps if s.tier == Tier.OPTIONAL),
                },
            },
        }
