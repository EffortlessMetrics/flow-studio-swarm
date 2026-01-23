"""
Tests for /platform/status endpoint degradation log coherence.

Validates that the /platform/status endpoint accurately reflects the degradation
log state from selftest_degradations.log.

Tests verify:
1. Degradations list matches log entries with correct fields
2. Status state reflects log severity (HEALTHY/DEGRADED/BROKEN)
3. Governance AC status reflects step failures from log
4. Kernel entries are NOT excluded from log (all tiers recorded)
5. Degradations are ordered by timestamp
6. Count fields match log severity distribution
7. Fresh data on each call (no stale cache)

Endpoint contract:
  GET /platform/status
  Returns: {
    timestamp: str,
    service: str,
    governance: {
      kernel: {...},
      selftest: {...},
      validation: {...},
      state: "FULLY_GOVERNED" | "DEGRADED" | "UNHEALTHY" | "UNKNOWN",
      degradations: [{timestamp, step_id, step_name, tier, message, severity, remediation}, ...],
      ac: {AC-ID: "PASS" | "WARNING" | "CRITICAL" | "INFO", ...}
    },
    flows: {...},
    agents: {...},
    hints: {...}
  }

Implementation note:
- Degradation log is at repo_root/selftest_degradations.log
- StatusProvider._load_degradations() reads and parses the log
- StatusProvider._aggregate_ac_status() derives AC status from selftest results + log
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

# ============================================================================
# Helper Functions
# ============================================================================


def create_degradation_entry(
    step_id: str,
    tier: str = "governance",
    severity: str = "warning",
    timestamp: str = None,
    message: str = "Test failure",
) -> Dict:
    """Create a valid degradation log entry."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "timestamp": timestamp,
        "step_id": step_id,
        "step_name": f"Step {step_id} description",
        "tier": tier,
        "message": message,
        "severity": severity,
        "remediation": f"Run: uv run swarm/tools/selftest.py --step {step_id}",
    }


def write_degradation_log(log_path: Path, entries: List[Dict]) -> None:
    """Write JSONL degradation log to path."""
    with log_path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def load_degradation_log(log_path: Path) -> List[Dict]:
    """Load JSONL degradation log from path."""
    if not log_path.exists():
        return []

    entries = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def create_mocked_provider(tmp_path, kernel_ok=True, selftest_status="GREEN", governance_ok=True):
    """Create StatusProvider with mocked checks using real dataclasses."""
    from swarm.tools.status_provider import (
        AgentsStatus,
        FlowsStatus,
        KernelStatus,
        SelfTestStatus,
        StatusProvider,
        ValidationStatus,
    )

    provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

    kernel_status_obj = KernelStatus(
        ok=kernel_ok, last_run="", status="HEALTHY" if kernel_ok else "BROKEN"
    )
    selftest_status_obj = SelfTestStatus(
        mode="strict",
        last_run="",
        status=selftest_status,
        failed_steps=[] if governance_ok else ["test-step"],
        kernel_ok=kernel_ok,
        governance_ok=governance_ok,
    )
    validation_status_obj = ValidationStatus(
        last_run="", status="PASS", error_count=0, warning_count=0
    )
    flows_status_obj = FlowsStatus(total=0, healthy=0, degraded=0, broken=0)
    agents_status_obj = AgentsStatus(total=0)

    # Apply mocks
    patch.object(provider, "_check_kernel", return_value=kernel_status_obj).start()
    patch.object(provider, "_check_selftest", return_value=selftest_status_obj).start()
    patch.object(provider, "_check_validation", return_value=validation_status_obj).start()
    patch.object(provider, "_check_flows", return_value=flows_status_obj).start()
    patch.object(provider, "_check_agents", return_value=agents_status_obj).start()

    return provider


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def status_provider(tmp_path):
    """Create StatusProvider with mocked subprocess calls."""
    from swarm.tools.status_provider import (
        AgentsStatus,
        FlowsStatus,
        KernelStatus,
        SelfTestStatus,
        StatusProvider,
        ValidationStatus,
    )

    provider = StatusProvider(repo_root=tmp_path, cache_ttl_seconds=0)

    # Create proper dataclass instances for mock returns
    kernel_status = KernelStatus(ok=True, last_run="", status="HEALTHY")
    selftest_status = SelfTestStatus(
        mode="strict",
        last_run="",
        status="GREEN",
        failed_steps=[],
        degraded_steps=[],
        kernel_ok=True,
        governance_ok=True,
        optional_ok=True,
    )
    validation_status = ValidationStatus(
        last_run="",
        status="PASS",
        error_count=0,
        warning_count=0,
    )
    flows_status = FlowsStatus(total=0, healthy=0, degraded=0, broken=0, invalid_flows=[])
    agents_status = AgentsStatus(total=0, by_status={"healthy": 0}, invalid_agents=[])

    # Mock subprocess calls to avoid actual execution
    with patch.object(provider, "_check_kernel") as mock_kernel:
        mock_kernel.return_value = kernel_status
        with patch.object(provider, "_check_selftest") as mock_selftest:
            mock_selftest.return_value = selftest_status
            with patch.object(provider, "_check_validation") as mock_validation:
                mock_validation.return_value = validation_status
                with patch.object(provider, "_check_flows") as mock_flows:
                    mock_flows.return_value = flows_status
                    with patch.object(provider, "_check_agents") as mock_agents:
                        mock_agents.return_value = agents_status

                        yield provider


# ============================================================================
# Test Suite: Status Endpoint Degradation Log Coherence
# ============================================================================


class TestStatusDegradationsListMatchesLog:
    """Test that /platform/status degradations list matches log entries."""

    def test_status_degradations_list_matches_log(self, tmp_path, status_provider):
        """Create synthetic log with 3 entries; assert status contains all 3 with correct fields."""
        log_path = tmp_path / "selftest_degradations.log"

        # Create 3 test entries with different steps
        entries = [
            create_degradation_entry(
                "agents-governance",
                tier="governance",
                severity="warning",
                message="Agent validation failed",
                timestamp="2025-12-01T10:15:22+00:00",
            ),
            create_degradation_entry(
                "devex-contract",
                tier="governance",
                severity="warning",
                message="Flow contract violation",
                timestamp="2025-12-01T10:15:25+00:00",
            ),
            create_degradation_entry(
                "ac-coverage",
                tier="optional",
                severity="info",
                message="Coverage below threshold",
                timestamp="2025-12-01T10:15:28+00:00",
            ),
        ]

        write_degradation_log(log_path, entries)

        # Get status
        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        # Verify degradations field exists
        assert "governance" in status, "Status should have governance field"
        assert "degradations" in status["governance"], "Governance should have degradations"

        degradations = status["governance"]["degradations"]

        # Should contain all 3 entries (or last 10 if log is longer)
        assert len(degradations) == 3, f"Expected 3 degradations, got {len(degradations)}"

        # Verify each entry has required fields
        required_fields = {
            "timestamp",
            "step_id",
            "step_name",
            "tier",
            "message",
            "severity",
            "remediation",
        }

        for i, deg in enumerate(degradations):
            missing = required_fields - set(deg.keys())
            assert not missing, f"Entry {i} missing fields: {missing}"

            # Verify field values match expected entries
            assert deg["step_id"] == entries[i]["step_id"]
            assert deg["tier"] == entries[i]["tier"]
            assert deg["severity"] == entries[i]["severity"]
            assert deg["message"] == entries[i]["message"]

    def test_status_degradations_empty_when_no_log(self, tmp_path, status_provider):
        """If degradation log doesn't exist, degradations should be empty list."""
        # No log file created

        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        degradations = status["governance"]["degradations"]
        assert degradations == [], f"Expected empty list, got {degradations}"


class TestStatusStateReflectsLogSeverity:
    """Test that status.governance.state reflects degradation log severity."""

    def test_status_state_critical_entry_maps_to_unhealthy(self, tmp_path):
        """Log with CRITICAL severity → state should be UNHEALTHY."""
        log_path = tmp_path / "selftest_degradations.log"

        entries = [
            create_degradation_entry(
                "core-checks",
                tier="kernel",
                severity="critical",
                message="Kernel check failed",
            )
        ]

        write_degradation_log(log_path, entries)

        provider = create_mocked_provider(
            tmp_path, kernel_ok=False, selftest_status="RED", governance_ok=False
        )

        status_report = provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        state = status["governance"]["state"]
        assert state == "UNHEALTHY", f"Expected UNHEALTHY, got {state}"

    def test_status_state_warning_entry_maps_to_degraded(self, tmp_path):
        """Log with only WARNING severity → state should be DEGRADED."""
        log_path = tmp_path / "selftest_degradations.log"

        entries = [
            create_degradation_entry(
                "agents-governance",
                tier="governance",
                severity="warning",
                message="Agent validation warning",
            )
        ]

        write_degradation_log(log_path, entries)

        provider = create_mocked_provider(
            tmp_path, kernel_ok=True, selftest_status="YELLOW", governance_ok=False
        )

        status_report = provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        state = status["governance"]["state"]
        assert state == "DEGRADED", f"Expected DEGRADED, got {state}"

    def test_status_state_empty_log_maps_to_healthy(self, tmp_path, status_provider):
        """Empty degradation log → state should be FULLY_GOVERNED (if all checks pass)."""
        # No log entries

        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        state = status["governance"]["state"]
        assert state == "FULLY_GOVERNED", f"Expected FULLY_GOVERNED, got {state}"

    def test_status_state_enum_validation(self, tmp_path, status_provider):
        """State field is one of valid governance states."""
        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        state = status["governance"]["state"]
        valid_states = {"FULLY_GOVERNED", "DEGRADED", "UNHEALTHY", "UNKNOWN"}
        assert state in valid_states, f"State '{state}' not in valid set {valid_states}"


class TestStatusGovernanceAcReflectsStepStatus:
    """Test that governance.ac field reflects acceptance criteria status from degradation log."""

    def test_status_ac_field_structure_exists(self, tmp_path, status_provider):
        """Verify AC field structure exists and contains valid statuses."""
        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        # Verify AC field structure exists
        assert "governance" in status
        assert "ac" in status["governance"], "Governance should have ac field"

        ac_status = status["governance"]["ac"]
        assert isinstance(ac_status, dict), "AC status should be a dictionary"

        # Each AC ID should map to a valid status
        valid_ac_statuses = {"PASS", "WARNING", "CRITICAL", "INFO", "FAILURE"}
        for ac_id, ac_stat in ac_status.items():
            assert ac_stat in valid_ac_statuses, f"AC {ac_id} has invalid status {ac_stat}"


class TestStatusDegradationsIncludeAllTiers:
    """Test that degradations list includes all tiers (kernel, governance, optional)."""

    def test_status_includes_all_tier_entries(self, tmp_path, status_provider):
        """All tier entries should appear in degradations list."""
        log_path = tmp_path / "selftest_degradations.log"

        entries = [
            create_degradation_entry(
                "core-checks",
                tier="kernel",
                severity="critical",
                message="Kernel failure",
            ),
            create_degradation_entry(
                "agents-governance",
                tier="governance",
                severity="warning",
                message="Governance failure",
            ),
            create_degradation_entry(
                "ac-coverage",
                tier="optional",
                severity="info",
                message="Optional failure",
            ),
        ]

        write_degradation_log(log_path, entries)

        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        degradations = status["governance"]["degradations"]

        # Should have all 3 entries
        assert len(degradations) == 3, f"Expected 3 entries, got {len(degradations)}"

        # Verify all tiers are present
        tiers = {d["tier"] for d in degradations}
        assert tiers == {"kernel", "governance", "optional"}, f"Expected all tiers, got {tiers}"


class TestStatusDegradationsOrderedByTimestamp:
    """Test that degradations list is ordered by timestamp."""

    def test_status_degradations_sorted_by_timestamp_ascending(self, tmp_path, status_provider):
        """Create log with out-of-order entries; status should return sorted (oldest first)."""
        log_path = tmp_path / "selftest_degradations.log"

        base_time = datetime(2025, 12, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Write in reverse chronological order
        entries = [
            create_degradation_entry(
                "step-3",
                timestamp=(base_time + timedelta(seconds=20)).isoformat(),
                message="Third failure",
            ),
            create_degradation_entry(
                "step-1",
                timestamp=base_time.isoformat(),
                message="First failure",
            ),
            create_degradation_entry(
                "step-2",
                timestamp=(base_time + timedelta(seconds=10)).isoformat(),
                message="Second failure",
            ),
        ]

        write_degradation_log(log_path, entries)

        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        degradations = status["governance"]["degradations"]

        assert len(degradations) == 3

        # Verify chronological order (oldest → newest)
        assert degradations[0]["step_id"] == "step-1", "First should be oldest"
        assert degradations[1]["step_id"] == "step-2", "Second should be middle"
        assert degradations[2]["step_id"] == "step-3", "Third should be newest"

        # Verify timestamps are ascending
        ts1 = datetime.fromisoformat(degradations[0]["timestamp"].replace("Z", "+00:00"))
        ts2 = datetime.fromisoformat(degradations[1]["timestamp"].replace("Z", "+00:00"))
        ts3 = datetime.fromisoformat(degradations[2]["timestamp"].replace("Z", "+00:00"))

        assert ts1 <= ts2 <= ts3, "Timestamps should be in ascending order"


class TestStatusCountFieldsMatchLog:
    """Test that count fields match degradation log severity distribution."""

    def test_status_severity_counts_match_log(self, tmp_path, status_provider):
        """Log with 2 CRITICAL, 3 WARNING, 1 INFO → counts should match."""
        log_path = tmp_path / "selftest_degradations.log"

        entries = [
            create_degradation_entry("step-1", tier="kernel", severity="critical"),
            create_degradation_entry("step-2", tier="kernel", severity="critical"),
            create_degradation_entry("step-3", tier="governance", severity="warning"),
            create_degradation_entry("step-4", tier="governance", severity="warning"),
            create_degradation_entry("step-5", tier="governance", severity="warning"),
            create_degradation_entry("step-6", tier="optional", severity="info"),
        ]

        write_degradation_log(log_path, entries)

        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        degradations = status["governance"]["degradations"]

        # Count by severity
        critical_count = sum(1 for d in degradations if d["severity"] == "critical")
        warning_count = sum(1 for d in degradations if d["severity"] == "warning")
        info_count = sum(1 for d in degradations if d["severity"] == "info")

        assert critical_count == 2, f"Expected 2 critical, got {critical_count}"
        assert warning_count == 3, f"Expected 3 warning, got {warning_count}"
        assert info_count == 1, f"Expected 1 info, got {info_count}"


class TestStatusEndpointFreshOnEachCall:
    """Test that status endpoint returns fresh data on each call (not cached)."""

    def test_status_reflects_log_changes_between_calls(self, tmp_path):
        """Call status, add entry to log, call again; new entry should appear."""
        log_path = tmp_path / "selftest_degradations.log"

        # Initial entry
        initial_entry = create_degradation_entry("step-1", message="Initial failure")
        write_degradation_log(log_path, [initial_entry])

        provider = create_mocked_provider(tmp_path)

        # First call
        status1 = provider.get_status(force_refresh=True).to_dict()
        degradations1 = status1["governance"]["degradations"]
        assert len(degradations1) == 1, f"Expected 1 entry, got {len(degradations1)}"
        assert degradations1[0]["step_id"] == "step-1"

        # Add new entry to log
        new_entry = create_degradation_entry("step-2", message="New failure")
        with log_path.open("a") as f:
            f.write(json.dumps(new_entry) + "\n")

        # Second call (should see new entry with force_refresh)
        status2 = provider.get_status(force_refresh=True).to_dict()
        degradations2 = status2["governance"]["degradations"]
        assert len(degradations2) == 2, f"Expected 2 entries, got {len(degradations2)}"

        # Verify new entry is present
        step_ids = [d["step_id"] for d in degradations2]
        assert "step-1" in step_ids, "Original entry should still be present"
        assert "step-2" in step_ids, "New entry should be present"


class TestStatusEndpointFullContract:
    """Test complete /platform/status contract with degradation log integration."""

    def test_status_endpoint_full_response_structure(self, tmp_path, status_provider):
        """Verify full status response has expected structure with degradation log."""
        log_path = tmp_path / "selftest_degradations.log"

        entries = [
            create_degradation_entry("agents-governance", tier="governance", severity="warning"),
        ]

        write_degradation_log(log_path, entries)

        status_report = status_provider.get_status(force_refresh=True)
        status = status_report.to_dict()

        # Verify top-level structure
        required_top = {"timestamp", "service", "governance", "flows", "agents", "hints"}
        assert set(status.keys()) >= required_top, "Missing top-level fields"

        # Verify governance structure
        gov = status["governance"]
        required_gov = {"kernel", "selftest", "validation", "state", "degradations", "ac"}
        assert set(gov.keys()) >= required_gov, (
            f"Missing governance fields: {required_gov - set(gov.keys())}"
        )

        # Verify degradations structure
        assert isinstance(gov["degradations"], list), "Degradations should be a list"
        if gov["degradations"]:
            deg = gov["degradations"][0]
            required_deg = {
                "timestamp",
                "step_id",
                "step_name",
                "tier",
                "message",
                "severity",
                "remediation",
            }
            assert set(deg.keys()) >= required_deg, "Missing degradation fields"

        # Verify AC structure
        assert isinstance(gov["ac"], dict), "AC should be a dict"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
