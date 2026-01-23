"""
SelfTest Report Schema

Defines the JSON structure for selftest reports.

Example JSON output:
{
  "metadata": {
    "run_id": "flow-3-abc123",
    "timestamp": "2025-11-30T15:30:00Z",
    "hostname": "macbook-pro",
    "platform": "darwin",
    "git_branch": "flow-3-selftest-enhancement",
    "git_commit": "9556a5b...",
    "user": "alice",
    "mode": "strict"
  },
  "results": [
    {
      "step_id": "core-checks",
      "description": "Rust cargo fmt, clippy, and unit tests",
      "tier": "kernel",
      "severity": "critical",
      "category": "correctness",
      "status": "PASS",
      "exit_code": 0,
      "duration_ms": 3500,
      "command": "cargo fmt --check && cargo clippy ... && cargo test ...",
      "timestamp_start": 1234567890.123,
      "timestamp_end": 1234567893.623
    }
  ],
  "summary": {
    "passed": 8,
    "failed": 1,
    "skipped": 1,
    "total": 10,
    "critical_passed": 1,
    "critical_failed": 0,
    "warning_passed": 5,
    "warning_failed": 1,
    "info_passed": 2,
    "info_failed": 0,
    "category_security_passed": 0,
    "category_security_failed": 0,
    "category_correctness_passed": 2,
    "category_correctness_failed": 0,
    "category_performance_passed": 0,
    "category_performance_failed": 0,
    "category_governance_passed": 6,
    "category_governance_failed": 1,
    "total_duration_ms": 15000
  }
}
"""

import json
from dataclasses import asdict, dataclass
from typing import List, Optional


@dataclass
class SelfTestReportMetadata:
    """Metadata about selftest execution."""

    run_id: str
    timestamp: str  # ISO format: 2025-11-30T15:30:00Z
    hostname: str
    platform: str  # e.g., "linux", "darwin", "win32"
    git_branch: str
    git_commit: str
    user: str  # from $USER env var
    mode: str  # "strict" | "degraded" | "kernel-only"


@dataclass
class SelfTestStepResult:
    """Result of a single selftest step."""

    step_id: str
    description: str
    tier: str
    severity: str
    category: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    exit_code: int
    duration_ms: int
    command: str
    timestamp_start: float
    timestamp_end: float
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclass
class SelfTestSummary:
    """Summary statistics for selftest run."""

    # By status
    passed: int
    failed: int
    skipped: int
    total: int

    # By severity
    critical_passed: int
    critical_failed: int
    warning_passed: int
    warning_failed: int
    info_passed: int
    info_failed: int

    # By category
    category_security_passed: int
    category_security_failed: int
    category_performance_passed: int
    category_performance_failed: int
    category_correctness_passed: int
    category_correctness_failed: int
    category_governance_passed: int
    category_governance_failed: int

    total_duration_ms: int


@dataclass
class SelfTestReport:
    """Complete selftest report."""

    metadata: SelfTestReportMetadata
    results: List[SelfTestStepResult]
    summary: SelfTestSummary

    def to_dict(self) -> dict:
        return {
            "metadata": asdict(self.metadata),
            "results": [asdict(r) for r in self.results],
            "summary": asdict(self.summary),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)
