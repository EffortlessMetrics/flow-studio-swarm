#!/usr/bin/env python3
"""
status_provider.py - Governance status tracking for Flow Studio

Provides a unified status endpoint that tracks:
- Kernel health (cargo fmt, clippy, tests)
- Selftest governance status (governance steps pass/fail/degrade)
- Flow validity (all 6 flows loadable and valid)
- Agent health (all agents registered and valid)

Usage:
    from status_provider import StatusProvider
    provider = StatusProvider(repo_root=Path(...))
    status = provider.get_status()  # Returns StatusReport
    print(status.to_json())
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.utils.yaml_utils import load_yaml

# Default cache TTL: 5 minutes for local dev, configurable via env
# Short TTL (30s) was causing excessive subprocess calls on page load
DEFAULT_STATUS_CACHE_TTL = int(os.getenv("FLOW_STUDIO_STATUS_TTL_SECONDS", "300"))


@dataclass
class KernelStatus:
    """Kernel health (cargo fmt, clippy, tests)."""
    ok: bool
    last_run: str  # ISO format timestamp
    status: str  # HEALTHY, BROKEN
    error: Optional[str] = None


@dataclass
class SelfTestStatus:
    """Governance selftest status."""
    mode: str  # "strict", "degraded"
    last_run: str  # ISO format timestamp
    status: str  # GREEN, YELLOW, RED
    failed_steps: List[str] = field(default_factory=list)  # Critical-only (preserves old meaning)
    degraded_steps: List[str] = field(default_factory=list)  # Warning + info failures

    # NEW: Union of all failures (critical + degraded) for UI
    all_failed_steps: List[str] = field(default_factory=list)

    # Severity breakdown
    kernel_ok: bool = True  # All CRITICAL steps passed
    governance_ok: bool = True  # All WARNING steps passed
    optional_ok: bool = True  # All INFO steps passed

    # Per-severity details
    critical_passed: int = 0
    critical_failed: int = 0
    warning_passed: int = 0
    warning_failed: int = 0
    info_passed: int = 0
    info_failed: int = 0

    # Tier-specific failure lists for UI
    kernel_failed: List[str] = field(default_factory=list)
    governance_failed: List[str] = field(default_factory=list)
    optional_failed: List[str] = field(default_factory=list)


@dataclass
class FlowsStatus:
    """Flow validity status."""
    total: int
    healthy: int
    degraded: int
    broken: int
    invalid_flows: List[str] = field(default_factory=list)


@dataclass
class AgentsStatus:
    """Agent validity status."""
    total: int
    by_status: Dict[str, int] = field(default_factory=lambda: {
        "healthy": 0,
        "misconfigured": 0,
        "unknown": 0,
    })
    invalid_agents: List[str] = field(default_factory=list)


@dataclass
class SelftestSnapshot:
    """Snapshot of selftest status from artifacts."""
    mode: str  # "strict", "degraded", "kernel-only", "unknown"
    status: str  # "GREEN", "YELLOW", "RED", "UNKNOWN"
    kernel_ok: bool
    governance_ok: bool
    optional_ok: bool
    failed_steps: List[str] = field(default_factory=list)
    kernel_failed: List[str] = field(default_factory=list)
    governance_failed: List[str] = field(default_factory=list)
    optional_failed: List[str] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "SelftestSnapshot":
        """Create an empty snapshot."""
        return cls(
            mode="unknown",
            status="UNKNOWN",
            kernel_ok=True,
            governance_ok=True,
            optional_ok=True,
        )


@dataclass
class Hints:
    """Hints for remediation."""
    if_kernel_broken: str
    if_selftest_broken: str
    how_to_heal: str


@dataclass
class ValidationStatus:
    """Validation results from validate_swarm.py."""
    last_run: str  # ISO format timestamp
    status: str  # PASS, FAIL, ERROR
    error_count: int = 0
    warning_count: int = 0
    agents_with_issues: List[str] = field(default_factory=list)
    flows_with_issues: List[str] = field(default_factory=list)
    steps_with_issues: List[str] = field(default_factory=list)
    # Detailed per-entity data for overlays
    agents: Dict[str, Any] = field(default_factory=dict)
    flows: Dict[str, Any] = field(default_factory=dict)
    steps: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class StatusReport:
    """Complete governance status report."""
    timestamp: str  # ISO format
    service: str  # "flow-studio"
    governance: Dict[str, Any]  # kernel, selftest, validation, state
    flows: Dict[str, Any]
    agents: Dict[str, Any]
    hints: Dict[str, str]
    selftest: Optional[SelfTestStatus] = None  # For direct access to selftest status
    validation: Optional[ValidationStatus] = None  # For direct access to validation status

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base_dict = asdict(self)
        # Remove the redundant selftest and validation fields from the dict since they're in governance
        if "selftest" in base_dict:
            del base_dict["selftest"]
        if "validation" in base_dict:
            del base_dict["validation"]
        return base_dict

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


def get_selftest_summary(*, degraded: bool = False) -> SelftestSnapshot:
    """
    Run the selftest engine in-process and return the canonical summary
    object used by /platform/status.

    This is a fast-path helper to avoid shelling out to the selftest CLI
    for local status checks (e.g., Flow Studio smoke).

    Args:
        degraded: If True, run in degraded mode (only KERNEL failures block)

    Returns:
        SelftestSnapshot with kernel_ok, governance_ok, failed_steps, etc.
    """
    # Local imports to avoid circular import at module load time
    import io
    import os
    import sys

    tools_path = os.path.dirname(__file__)
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)

    from selftest import SelfTestRunner
    from selftest_config import get_steps_in_order

    # Skip flowstudio-smoke to avoid recursion (this function is called BY flowstudio-smoke)
    skip_steps = {"flowstudio-smoke"}

    runner = SelfTestRunner(
        degraded=degraded,
        kernel_only=False,
        verbose=False,
        json_output=True,  # Use JSON mode to suppress human-readable output
        json_v2=False,
        write_report=False,  # don't write report artifacts here
        skip_steps=skip_steps,
    )

    # Suppress stdout during selftest run to avoid polluting the smoke test output
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        steps = get_steps_in_order()
        runner.run(steps)
    finally:
        sys.stdout = old_stdout

    summary = runner.build_summary()

    # Determine status from kernel/governance/optional health
    kernel_ok = summary.get("kernel_ok", True)
    governance_ok = summary.get("governance_ok", True)
    optional_ok = summary.get("optional_ok", True)

    if not kernel_ok:
        status = "RED"
    elif not governance_ok:
        status = "YELLOW"
    else:
        status = "GREEN"

    return SelftestSnapshot(
        mode=summary.get("mode", "strict"),
        status=status,
        kernel_ok=kernel_ok,
        governance_ok=governance_ok,
        optional_ok=optional_ok,
        failed_steps=summary.get("failed_steps", []) or [],
        kernel_failed=summary.get("kernel_failed", []) or [],
        governance_failed=summary.get("governance_failed", []) or [],
        optional_failed=summary.get("optional_failed", []) or [],
    )


class StatusProvider:
    """Provides governance status with optional caching."""

    def __init__(self, repo_root: Path = None, cache_ttl_seconds: int = None):
        """
        Initialize status provider.

        Args:
            repo_root: Root of the Flow Studio repo (defaults to parent of tools/)
            cache_ttl_seconds: Cache status for this many seconds (0 = no cache).
                              Defaults to FLOW_STUDIO_STATUS_TTL_SECONDS env var,
                              or 300s (5 min) if not set. Use 30s or less for CI.
        """
        if cache_ttl_seconds is None:
            cache_ttl_seconds = DEFAULT_STATUS_CACHE_TTL
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[2]
        self.repo_root = repo_root
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_status: Optional[StatusReport] = None
        self._cache_timestamp: float = 0.0
        # Lock to prevent cache stampede when multiple threads try to refresh
        self._refresh_lock = threading.Lock()

    def _load_selftest_snapshot(self) -> SelftestSnapshot:
        """
        Load selftest snapshot from selftest_report.json artifact.

        Returns:
            SelftestSnapshot with status and metadata from last run
        """
        # Try to find selftest report in standard location
        report_path = self.repo_root / "swarm" / "runs" / "main" / "build" / "selftest_report.json"

        if not report_path.exists():
            return SelftestSnapshot.empty()

        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return SelftestSnapshot.empty()

        summary = data.get("summary", {})

        # Determine status from kernel/governance/optional health
        kernel_ok = summary.get("kernel_ok", True)
        governance_ok = summary.get("governance_ok", True)
        optional_ok = summary.get("optional_ok", True)

        if not kernel_ok:
            status = "RED"
        elif not governance_ok:
            status = "YELLOW"
        else:
            status = "GREEN"

        return SelftestSnapshot(
            mode=summary.get("mode", "unknown"),
            status=status,
            kernel_ok=kernel_ok,
            governance_ok=governance_ok,
            optional_ok=optional_ok,
            failed_steps=summary.get("failed_steps", []) or [],
            kernel_failed=summary.get("kernel_failed", []) or [],
            governance_failed=summary.get("governance_failed", []) or [],
            optional_failed=summary.get("optional_failed", []) or [],
        )

    def _load_degradations(self) -> List[Dict[str, Any]]:
        """
        Load degradation log entries from selftest_degradations.log.

        Returns:
            List of degradation entries (JSON objects), sorted by timestamp
        """
        log_path = self.repo_root / "selftest_degradations.log"

        if not log_path.exists():
            return []

        entries: List[Dict[str, Any]] = []
        try:
            with log_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []

        # Sort oldest → newest by timestamp
        entries.sort(key=lambda e: e.get("timestamp", ""))
        return entries

    def _aggregate_ac_status(self) -> Dict[str, str]:
        """
        Aggregate AC (Acceptance Criteria) status from selftest plan and results.

        Logic:
        - For each AC ID declared in the plan, determine overall status based on:
          - CRITICAL (or FAILURE): Step with this AC failed
          - WARNING: Step with this AC passed but another step with same AC failed
          - PASS: All steps with this AC passed

        Status precedence (worst wins):
        - CRITICAL > FAILURE > WARNING > INFO > PASS

        Returns:
            Dict[str, str]: Mapping of AC ID → status (e.g., {"AC-SELFTEST-KERNEL-FAST": "PASS"})
        """
        ac_status: Dict[str, str] = {}

        try:
            # Import selftest config to get step→AC mapping
            import os
            import sys
            tools_path = os.path.dirname(__file__)
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)

            from selftest_config import SELFTEST_STEPS

            # Build AC → [step_ids] map
            ac_to_steps: Dict[str, List[str]] = {}
            for step in SELFTEST_STEPS:
                for ac_id in step.ac_ids:
                    if ac_id not in ac_to_steps:
                        ac_to_steps[ac_id] = []
                    ac_to_steps[ac_id].append(step.id)

            # Load selftest snapshot to get step results
            snapshot = self._load_selftest_snapshot()

            # For each AC, determine status based on worst step result
            for ac_id, step_ids in ac_to_steps.items():
                step_statuses: List[str] = []

                # Collect status for each step that claims this AC
                for step_id in step_ids:
                    if step_id in snapshot.failed_steps:
                        # Check severity: kernel_failed → CRITICAL, governance_failed → WARNING
                        if step_id in snapshot.kernel_failed:
                            step_statuses.append("CRITICAL")
                        elif step_id in snapshot.governance_failed:
                            step_statuses.append("WARNING")
                        else:
                            step_statuses.append("FAILURE")
                    elif step_id in snapshot.optional_failed:
                        step_statuses.append("INFO")
                    else:
                        step_statuses.append("PASS")

                # Determine worst status (precedence: CRITICAL > FAILURE > WARNING > INFO > PASS)
                status_precedence = {"CRITICAL": 5, "FAILURE": 4, "WARNING": 3, "INFO": 2, "PASS": 1}
                worst_status = max(step_statuses, key=lambda s: status_precedence.get(s, 0)) if step_statuses else "PASS"
                ac_status[ac_id] = worst_status

        except Exception as e:
            # If selftest config unavailable, return empty dict
            # This is graceful degradation; the endpoint will still return status.
            import sys
            if hasattr(sys, 'stderr'):
                print(f"Debug: Could not aggregate AC status: {e}", file=sys.stderr)
            return {}

        return ac_status

    def get_status(self, force_refresh: bool = False) -> StatusReport:
        """
        Get current governance status (uses cache if available).

        Uses a lock to prevent cache stampede when multiple threads
        discover a stale cache simultaneously. This is important because
        /platform/status runs in a threadpool, so concurrent requests
        can try to refresh at the same time.

        Args:
            force_refresh: Bypass cache and recompute

        Returns:
            StatusReport with full governance status
        """
        now = time.time()

        # Fast path: return cached result if fresh (no lock needed)
        if (
            not force_refresh
            and self._cached_status is not None
            and (now - self._cache_timestamp) < self.cache_ttl_seconds
        ):
            return self._cached_status

        # Slow path: acquire lock to prevent stampede
        with self._refresh_lock:
            # Re-check after acquiring lock (another thread may have refreshed)
            now = time.time()
            if (
                not force_refresh
                and self._cached_status is not None
                and (now - self._cache_timestamp) < self.cache_ttl_seconds
            ):
                return self._cached_status

            # Actually compute the status
            status = self._compute_status()
            self._cached_status = status
            self._cache_timestamp = time.time()
            return status

    def _compute_status(self) -> StatusReport:
        """Compute full status from system state."""
        # Compute individual statuses
        kernel_status = self._check_kernel()
        selftest_status = self._check_selftest()
        validation_status = self._check_validation()
        flows_status = self._check_flows()
        agents_status = self._check_agents()

        # Load selftest snapshot and degradations from artifacts
        selftest_snapshot = self._load_selftest_snapshot()
        degradations = self._load_degradations()

        # Aggregate AC (Acceptance Criteria) status from selftest plan
        ac_status = self._aggregate_ac_status()

        # Determine overall governance state
        governance_state = self._determine_governance_state(
            kernel_status,
            selftest_status,
            validation_status,
        )

        # Build report
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # Build selftest dict with severity breakdown
        selftest_dict = asdict(selftest_status)

        # Build validation dict
        validation_dict = asdict(validation_status)

        # Build actionable hints based on state
        hints = self._build_hints(kernel_status, selftest_snapshot, validation_status)

        return StatusReport(
            timestamp=now_iso,
            service="flow-studio",
            governance={
                "kernel": asdict(kernel_status),
                "selftest": selftest_dict,
                "validation": validation_dict,
                "state": governance_state,
                "degradations": degradations[-10:] if degradations else [],  # Last 10
                "ac": ac_status,  # AC (Acceptance Criteria) status aggregation
            },
            flows=asdict(flows_status),
            agents=asdict(agents_status),
            hints=hints,
            selftest=selftest_status,
            validation=validation_status,
        )

    def _build_hints(
        self,
        kernel_status: KernelStatus,
        selftest_snapshot: SelftestSnapshot,
        validation_status: Optional[ValidationStatus],
    ) -> Dict[str, str]:
        """Build actionable hints based on current status."""
        hints: List[str] = []

        # Kernel hints
        if not kernel_status.ok:
            hints.append("⚠ KERNEL failure: This blocks all merges")
            hints.append("Run: uv run swarm/tools/kernel_smoke.py --verbose")
        elif selftest_snapshot.kernel_failed:
            hints.append("⚠ Selftest KERNEL failure(s):")
            for step_id in selftest_snapshot.kernel_failed:
                hints.append(f"  Run: uv run swarm/tools/selftest.py --step {step_id}")
        else:
            hints.append("✓ Kernel health check passed")

        # Governance hints
        if selftest_snapshot.governance_failed:
            hints.append("")
            hints.append("💡 Governance failure(s):")
            for step_id in selftest_snapshot.governance_failed:
                hints.append(f"  Run: uv run swarm/tools/selftest.py --step {step_id}")
            hints.append("  Or: uv run swarm/tools/selftest.py --degraded to work around")
        elif selftest_snapshot.governance_ok and selftest_snapshot.kernel_ok:
            hints.append("✓ All governance checks passed")

        # Degradation hints
        if selftest_snapshot.optional_failed:
            hints.append("")
            hints.append("ℹ Optional check failure(s):")
            for step_id in selftest_snapshot.optional_failed[:3]:  # Show first 3
                hints.append(f"  {step_id}")
            if len(selftest_snapshot.optional_failed) > 3:
                hints.append(f"  ... and {len(selftest_snapshot.optional_failed) - 3} more")
            hints.append("  Run: uv run swarm/tools/show_selftest_degradations.py to see all")

        # Validation hints
        if validation_status and validation_status.status == "FAIL":
            hints.append("")
            hints.append("⚠ Validation failed")
            hints.append("Run: uv run swarm/tools/validate_swarm.py for details")

        # General guidance
        hints.append("")
        hints.append("📖 Documentation:")
        hints.append("  Run: uv run swarm/tools/selftest.py --plan")
        hints.append("  See: docs/SELFTEST_SYSTEM.md")

        return {
            "summary": "; ".join(
                [
                    "KERNEL: " + ("✓" if selftest_snapshot.kernel_ok else "✗"),
                    "GOVERNANCE: " + ("✓" if selftest_snapshot.governance_ok else "✗"),
                    "OPTIONAL: " + ("✓" if selftest_snapshot.optional_ok else "⚠"),
                ]
            ),
            "detailed": "\n".join(hints),
        }

    def _check_kernel(self) -> KernelStatus:
        """Check kernel health (cargo fmt, clippy, tests)."""
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        try:
            # Run kernel smoke
            result = subprocess.run(
                ["uv", "run", "swarm/tools/kernel_smoke.py", "--json"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return KernelStatus(
                    ok=True,
                    last_run=now_iso,
                    status="HEALTHY",
                )
            else:
                # Parse error from output if available
                try:
                    data = json.loads(result.stdout)
                    failed = [k for k, v in data.get("results", {}).items() if not v.get("passed")]
                    error = f"Failed checks: {', '.join(failed)}"
                except (json.JSONDecodeError, KeyError):
                    error = "kernel-smoke failed"

                return KernelStatus(
                    ok=False,
                    last_run=now_iso,
                    status="BROKEN",
                    error=error,
                )
        except subprocess.TimeoutExpired:
            return KernelStatus(
                ok=False,
                last_run=now_iso,
                status="BROKEN",
                error="kernel-smoke timed out",
            )
        except Exception as e:
            return KernelStatus(
                ok=False,
                last_run=now_iso,
                status="BROKEN",
                error=str(e),
            )

    def _check_selftest(self) -> SelfTestStatus:
        """Check governance via selftest (if available)."""
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        try:
            # Try to run selftest
            result = subprocess.run(
                ["uv", "run", "swarm/tools/selftest.py", "--json"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=600,
            )
            data = json.loads(result.stdout)
            results = data.get("results", [])

            # Compute severity breakdown from results if summary not provided
            summary = data.get("summary", {})
            if not summary:
                # Build summary from results
                critical_passed = 0
                critical_failed = 0
                warning_passed = 0
                warning_failed = 0
                info_passed = 0
                info_failed = 0

                for step_result in results:
                    status_val = step_result.get("status", "")
                    severity = step_result.get("severity", "info")

                    # Count by severity and status
                    if severity == "critical":
                        if status_val == "PASS":
                            critical_passed += 1
                        elif status_val == "FAIL":
                            critical_failed += 1
                    elif severity == "warning":
                        if status_val == "PASS":
                            warning_passed += 1
                        elif status_val == "FAIL":
                            warning_failed += 1
                    elif severity == "info":
                        if status_val == "PASS":
                            info_passed += 1
                        elif status_val == "FAIL":
                            info_failed += 1

                summary = {
                    "critical_passed": critical_passed,
                    "critical_failed": critical_failed,
                    "warning_passed": warning_passed,
                    "warning_failed": warning_failed,
                    "info_passed": info_passed,
                    "info_failed": info_failed,
                }

            # Collect failures by tier and overall
            critical_failed_steps: List[str] = []
            degraded_steps: List[str] = []  # warning + info
            kernel_failed_list: List[str] = []
            governance_failed_list: List[str] = []
            optional_failed_list: List[str] = []

            for step_result in results:
                step_id = step_result.get("step_id", "")
                status_val = step_result.get("status", "")

                if status_val == "FAIL":
                    severity = step_result.get("severity", "info")

                    if severity == "critical":
                        critical_failed_steps.append(step_id)
                        kernel_failed_list.append(step_id)
                    elif severity == "warning":
                        degraded_steps.append(step_id)
                        governance_failed_list.append(step_id)
                    else:
                        # info-level failures are degradations
                        degraded_steps.append(step_id)
                        optional_failed_list.append(step_id)

            # Union for UI
            all_failed_steps = critical_failed_steps + degraded_steps

            # Determine overall status based on severity breakdown
            critical_failed = summary.get("critical_failed", 0)
            warning_failed = summary.get("warning_failed", 0)
            info_failed = summary.get("info_failed", 0)

            if critical_failed > 0:
                status = "RED"
            elif warning_failed > 0:
                status = "YELLOW"
            else:
                status = "GREEN"

            return SelfTestStatus(
                mode=data.get("mode", "strict"),
                last_run=now_iso,
                status=status,
                failed_steps=critical_failed_steps,  # preserves old critical-only meaning
                degraded_steps=degraded_steps,
                all_failed_steps=all_failed_steps,  # new union field for UI
                kernel_ok=critical_failed == 0,
                governance_ok=warning_failed == 0,
                optional_ok=info_failed == 0,
                critical_passed=summary.get("critical_passed", 0),
                critical_failed=critical_failed,
                warning_passed=summary.get("warning_passed", 0),
                warning_failed=warning_failed,
                info_passed=summary.get("info_passed", 0),
                info_failed=info_failed,
                kernel_failed=kernel_failed_list,
                governance_failed=governance_failed_list,
                optional_failed=optional_failed_list,
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # Selftest not available or parsing failed
            import sys
            print(f"Error parsing selftest report: {e}", file=sys.stderr)
            return SelfTestStatus(
                mode="unknown",
                last_run=now_iso,
                status="UNKNOWN",
                failed_steps=[],
                degraded_steps=[],
                all_failed_steps=[],
                kernel_ok=False,
                governance_ok=False,
                optional_ok=False,
                critical_passed=0,
                critical_failed=0,
                warning_passed=0,
                warning_failed=0,
                info_passed=0,
                info_failed=0,
                kernel_failed=[],
                governance_failed=[],
                optional_failed=[],
            )
        except subprocess.TimeoutExpired:
            return SelfTestStatus(
                mode="unknown",
                last_run=now_iso,
                status="RED",
                failed_steps=["selftest-timeout"],
                degraded_steps=[],
                all_failed_steps=["selftest-timeout"],
                kernel_ok=False,
                governance_ok=False,
                optional_ok=False,
                critical_passed=0,
                critical_failed=0,
                warning_passed=0,
                warning_failed=0,
                info_passed=0,
                info_failed=0,
                kernel_failed=["selftest-timeout"],
                governance_failed=[],
                optional_failed=[],
            )
        except Exception as e:
            # Selftest not available
            import sys
            print(f"Error checking selftest: {e}", file=sys.stderr)
            return SelfTestStatus(
                mode="unknown",
                last_run=now_iso,
                status="UNKNOWN",
                failed_steps=[],
                degraded_steps=[],
                all_failed_steps=[],
                kernel_ok=False,
                governance_ok=False,
                optional_ok=False,
                critical_passed=0,
                critical_failed=0,
                warning_passed=0,
                warning_failed=0,
                info_passed=0,
                info_failed=0,
                kernel_failed=[],
                governance_failed=[],
                optional_failed=[],
            )

    def _check_flows(self) -> FlowsStatus:
        """Check if all 6 flows are valid."""
        flows_dir = self.repo_root / "swarm" / "config" / "flows"
        total = 0
        healthy = 0
        broken = []

        if flows_dir.exists():
            for flow_file in sorted(flows_dir.glob("*.yaml")):
                try:
                    total += 1
                    data = load_yaml(flow_file.read_text(encoding="utf-8"))
                    if data and isinstance(data, dict) and data.get("key"):
                        healthy += 1
                    else:
                        broken.append(flow_file.stem)
                except Exception:
                    broken.append(flow_file.stem)

        return FlowsStatus(
            total=total,
            healthy=healthy,
            degraded=0,
            broken=len(broken),
            invalid_flows=broken,
        )

    def _check_agents(self) -> AgentsStatus:
        """Check if all agents are valid."""
        agents_dir = self.repo_root / "swarm" / "config" / "agents"
        total = 0
        healthy = 0
        misconfigured = []

        if agents_dir.exists():
            for agent_file in sorted(agents_dir.glob("*.yaml")):
                try:
                    total += 1
                    data = load_yaml(agent_file.read_text(encoding="utf-8"))
                    if (
                        data
                        and isinstance(data, dict)
                        and data.get("key")
                        and data.get("category")
                        and data.get("color")
                    ):
                        healthy += 1
                    else:
                        misconfigured.append(agent_file.stem)
                except Exception:
                    misconfigured.append(agent_file.stem)

        return AgentsStatus(
            total=total,
            by_status={
                "healthy": healthy,
                "misconfigured": len(misconfigured),
                "unknown": 0,
            },
            invalid_agents=misconfigured,
        )

    def _check_validation(self) -> ValidationStatus:
        """Run validate_swarm.py --json and parse results."""
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        try:
            result = subprocess.run(
                ["uv", "run", "swarm/tools/validate_swarm.py", "--json"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Parse JSON output (even on non-zero exit, JSON is printed to stdout)
            try:
                data = json.loads(result.stdout)
                summary = data.get("summary", {})

                return ValidationStatus(
                    last_run=data.get("timestamp", now_iso),
                    status=summary.get("status", "UNKNOWN"),
                    error_count=summary.get("failed", 0),
                    warning_count=summary.get("warnings", 0),
                    agents_with_issues=summary.get("agents_with_issues", []),
                    flows_with_issues=summary.get("flows_with_issues", []),
                    steps_with_issues=summary.get("steps_with_issues", []),
                    agents=data.get("agents", {}),
                    flows=data.get("flows", {}),
                    steps=data.get("steps", {}),
                )
            except (json.JSONDecodeError, KeyError) as e:
                return ValidationStatus(
                    last_run=now_iso,
                    status="ERROR",
                    error=f"Failed to parse validation output: {e}",
                )
        except subprocess.TimeoutExpired:
            return ValidationStatus(
                last_run=now_iso,
                status="ERROR",
                error="Validation timed out",
            )
        except Exception as e:
            return ValidationStatus(
                last_run=now_iso,
                status="ERROR",
                error=str(e),
            )

    def _determine_governance_state(
        self,
        kernel_status: KernelStatus,
        selftest_status: SelfTestStatus,
        validation_status: Optional[ValidationStatus] = None,
    ) -> str:
        """
        Determine overall governance state.

        Rules:
        - UNHEALTHY: kernel broken or validation failed
        - DEGRADED: kernel OK, but selftest has governance failures or validation has warnings
        - FULLY_GOVERNED: kernel OK, selftest green, validation passed, all flows/agents valid
        - UNKNOWN: unable to determine
        """
        if not kernel_status.ok:
            return "UNHEALTHY"

        if selftest_status.status == "RED":
            return "UNHEALTHY"

        # Check validation status
        if validation_status and validation_status.status == "FAIL":
            return "UNHEALTHY"

        if selftest_status.status == "YELLOW":
            return "DEGRADED"

        # Check for validation warnings
        if validation_status and validation_status.warning_count > 0:
            return "DEGRADED"

        if selftest_status.status == "UNKNOWN":
            return "UNKNOWN"

        if validation_status and validation_status.status == "ERROR":
            return "UNKNOWN"

        # Kernel OK, selftest GREEN, validation PASS
        return "FULLY_GOVERNED"
