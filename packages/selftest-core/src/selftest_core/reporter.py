"""
Report generation for selftest.

This module provides classes for generating and serializing selftest reports
in various formats including JSON and human-readable text.

Two report formats are supported:
- v1: Legacy format with basic status information
- v2: Extended format with severity/category breakdowns and full metadata

Example usage:
    from selftest_core import SelfTestRunner
    from selftest_core.reporter import ReportGenerator, ConsoleReporter

    runner = SelfTestRunner(steps)
    result = runner.run()

    # Generate JSON report
    generator = ReportGenerator(result)
    generator.write_json("selftest_report.json")

    # Print to console
    reporter = ConsoleReporter(result)
    reporter.print_summary()
"""

import json
import os
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO


@dataclass
class ReportMetadata:
    """
    Metadata about selftest execution environment.

    Captures context about where and when the selftest was run.

    Attributes:
        run_id: Unique identifier for this run
        timestamp: ISO 8601 timestamp
        hostname: Machine hostname
        platform: Operating system platform
        git_branch: Current git branch (if in git repo)
        git_commit: Current git commit hash (if in git repo)
        user: Username from environment
        mode: Selftest execution mode
    """
    run_id: str
    timestamp: str
    hostname: str
    platform: str
    git_branch: str
    git_commit: str
    user: str
    mode: str


@dataclass
class StepReport:
    """
    Report for a single step execution.

    Contains detailed information about a step's execution.
    """
    step_id: str
    description: str
    tier: str
    severity: str
    category: str
    status: str
    exit_code: int
    duration_ms: int
    command: str
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ReportSummary:
    """
    Summary statistics for a selftest run.

    Contains aggregate counts by status, severity, and category.
    """
    passed: int
    failed: int
    skipped: int
    total: int
    total_duration_ms: int
    by_severity: Dict[str, Dict[str, int]]
    by_category: Dict[str, Dict[str, int]]


class ReportGenerator:
    """
    Generates selftest reports in various formats.

    Takes raw runner results and produces formatted reports suitable
    for JSON export, logging, or display.
    """

    def __init__(
        self,
        result: Dict[str, Any],
        run_id: Optional[str] = None,
    ):
        """
        Initialize the report generator.

        Args:
            result: Runner result dictionary from SelfTestRunner.run()
            run_id: Optional run identifier (generated if not provided)
        """
        self.result = result
        self.run_id = run_id or f"selftest-{int(datetime.now().timestamp())}"

    def _get_git_branch(self) -> str:
        """Get current git branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return os.environ.get("GIT_BRANCH", "unknown")

    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return os.environ.get("CI_COMMIT_SHA", "unknown")

    def build_metadata(self) -> ReportMetadata:
        """Build report metadata from environment."""
        return ReportMetadata(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hostname=socket.gethostname(),
            platform=sys.platform,
            git_branch=self._get_git_branch(),
            git_commit=self._get_git_commit(),
            user=os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
            mode=self.result.get("mode", "unknown"),
        )

    def build_summary(self) -> ReportSummary:
        """Build report summary from results."""
        return ReportSummary(
            passed=self.result.get("passed", 0),
            failed=self.result.get("failed", 0),
            skipped=self.result.get("skipped", 0),
            total=self.result.get("total", 0),
            total_duration_ms=self.result.get("total_duration_ms", 0),
            by_severity=self.result.get("by_severity", {}),
            by_category=self.result.get("by_category", {}),
        )

    def to_dict_v1(self) -> Dict[str, Any]:
        """
        Generate v1 format report (legacy).

        Returns:
            Dictionary with basic report structure
        """
        return {
            "mode": self.result.get("mode", "unknown"),
            "passed": self.result.get("passed", 0),
            "failed": self.result.get("failed", 0),
            "skipped": self.result.get("skipped", 0),
            "total": self.result.get("total", 0),
            "total_time_ms": self.result.get("total_duration_ms", 0),
            "results": self.result.get("results", []),
        }

    def to_dict_v2(self) -> Dict[str, Any]:
        """
        Generate v2 format report (extended).

        Returns:
            Dictionary with full report including metadata and breakdowns
        """
        metadata = self.build_metadata()
        summary = self.build_summary()

        return {
            "version": "2.0",
            "metadata": asdict(metadata),
            "summary": asdict(summary),
            "results": self.result.get("results", []),
        }

    def to_json(self, version: str = "v2", indent: int = 2) -> str:
        """
        Generate JSON string report.

        Args:
            version: Report version ('v1' or 'v2')
            indent: JSON indentation level

        Returns:
            JSON string
        """
        if version == "v1":
            data = self.to_dict_v1()
        else:
            data = self.to_dict_v2()

        return json.dumps(data, indent=indent, default=str)

    def write_json(
        self,
        path: str,
        version: str = "v2",
        indent: int = 2,
    ) -> Path:
        """
        Write JSON report to file.

        Args:
            path: Output file path
            version: Report version ('v1' or 'v2')
            indent: JSON indentation level

        Returns:
            Path to written file
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(self.to_json(version=version, indent=indent))

        return output_path


class ConsoleReporter:
    """
    Reports selftest results to console.

    Provides human-readable output with status indicators,
    summaries, and optional verbose details.
    """

    def __init__(
        self,
        result: Dict[str, Any],
        verbose: bool = False,
        output: Optional[TextIO] = None,
    ):
        """
        Initialize the console reporter.

        Args:
            result: Runner result dictionary
            verbose: Include detailed output
            output: Output stream (default: sys.stdout)
        """
        self.result = result
        self.verbose = verbose
        self.output = output or sys.stdout

    def _print(self, *args, **kwargs):
        """Print to configured output."""
        print(*args, file=self.output, **kwargs)

    def print_header(self):
        """Print test header."""
        self._print("=" * 70)
        self._print("SELFTEST RUNNER")
        self._print("=" * 70)

        mode = self.result.get("mode", "unknown")
        if mode == "degraded":
            self._print("Mode: DEGRADED (only KERNEL failures block)")
        elif mode == "kernel-only":
            self._print("Mode: KERNEL-ONLY")
        else:
            self._print("Mode: STRICT (KERNEL and GOVERNANCE failures block)")
        self._print()

    def print_step_result(self, step_result: Dict[str, Any]):
        """Print individual step result."""
        step_id = step_result.get("step_id", "unknown")
        status = step_result.get("status", "UNKNOWN")
        duration = step_result.get("duration_ms", 0)

        status_str = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
        self._print(f"  [{status_str}] {step_id:30s} ({duration}ms)")

        if self.verbose and status == "FAIL":
            error = step_result.get("error", "")
            if error:
                self._print(f"        Error: {error[:200]}")

    def print_summary(self):
        """Print test summary."""
        self._print()
        self._print("=" * 70)
        self._print("SELFTEST SUMMARY")
        self._print("=" * 70)

        passed = self.result.get("passed", 0)
        failed = self.result.get("failed", 0)
        skipped = self.result.get("skipped", 0)
        total = self.result.get("total", 0)

        self._print(f"Passed:  {passed}/{total}")
        self._print(f"Failed:  {failed}/{total}")
        self._print(f"Skipped: {skipped}/{total}")

        failed_steps = self.result.get("failed_steps", [])
        if failed_steps:
            self._print("\nFailed steps:")
            for step_id in failed_steps:
                self._print(f"  - {step_id}")

        total_ms = self.result.get("total_duration_ms", 0)
        self._print(f"\nTotal time: {total_ms / 1000:.2f}s")

        # Print status
        status = self.result.get("status", "UNKNOWN")
        self._print(f"\nStatus: {status}")

    def print_severity_breakdown(self):
        """Print breakdown by severity."""
        by_severity = self.result.get("by_severity", {})
        if not by_severity:
            return

        self._print("\nBreakdown by Severity:")
        for sev in ["critical", "warning", "info"]:
            counts = by_severity.get(sev, {})
            passed = counts.get("passed", 0)
            failed = counts.get("failed", 0)
            self._print(f"  {sev:10s}: {passed:2d} passed, {failed:2d} failed")

    def print_category_breakdown(self):
        """Print breakdown by category."""
        by_category = self.result.get("by_category", {})
        if not by_category:
            return

        self._print("\nBreakdown by Category:")
        for cat in ["security", "performance", "correctness", "governance"]:
            counts = by_category.get(cat, {})
            passed = counts.get("passed", 0)
            failed = counts.get("failed", 0)
            self._print(f"  {cat:12s}: {passed:2d} passed, {failed:2d} failed")

    def print_hints(self):
        """Print actionable hints for failures."""
        kernel_failed = self.result.get("kernel_failed", [])
        governance_failed = self.result.get("governance_failed", [])

        if not kernel_failed and not governance_failed:
            return

        self._print("\nHints for resolution:")

        if kernel_failed:
            self._print("  KERNEL failure(s): This blocks all merges")
            for step_id in kernel_failed:
                self._print(f"    Run: selftest run --step {step_id}")

        if governance_failed:
            if kernel_failed:
                self._print()
            self._print("  GOVERNANCE failure(s): Run any of:")
            for step_id in governance_failed:
                self._print(f"    Run: selftest run --step {step_id}")
            if not kernel_failed:
                self._print("  Or try: selftest run --degraded to work around governance failures")

    def print_full_report(self):
        """Print complete report with all sections."""
        self.print_header()

        # Print individual results
        for step_result in self.result.get("results", []):
            self.print_step_result(step_result)

        self.print_summary()
        self.print_severity_breakdown()
        self.print_category_breakdown()
        self.print_hints()
