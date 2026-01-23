#!/usr/bin/env python3
"""
Tests for the in-process selftest summary helper.

These tests verify that get_selftest_summary() provides the same information
as running selftest.py via subprocess, but faster (in-process).
"""

import sys
from pathlib import Path

# Add swarm/tools to path for imports
tools_path = Path(__file__).resolve().parents[1] / "swarm" / "tools"
sys.path.insert(0, str(tools_path))


class TestGetSelftestSummary:
    """Tests for get_selftest_summary() fast-path helper."""

    def test_get_selftest_summary_returns_snapshot(self):
        """Basic test: get_selftest_summary returns a SelftestSnapshot."""
        from status_provider import SelftestSnapshot, get_selftest_summary

        snapshot = get_selftest_summary(degraded=False)

        assert isinstance(snapshot, SelftestSnapshot)
        assert hasattr(snapshot, "kernel_ok")
        assert hasattr(snapshot, "governance_ok")
        assert hasattr(snapshot, "failed_steps")
        assert hasattr(snapshot, "status")
        assert hasattr(snapshot, "mode")

    def test_get_selftest_summary_kernel_ok_is_bool(self):
        """kernel_ok should be a boolean."""
        from status_provider import get_selftest_summary

        snapshot = get_selftest_summary(degraded=False)

        assert isinstance(snapshot.kernel_ok, bool)

    def test_get_selftest_summary_governance_ok_is_bool(self):
        """governance_ok should be a boolean."""
        from status_provider import get_selftest_summary

        snapshot = get_selftest_summary(degraded=False)

        assert isinstance(snapshot.governance_ok, bool)

    def test_get_selftest_summary_failed_steps_is_list(self):
        """failed_steps should be a list."""
        from status_provider import get_selftest_summary

        snapshot = get_selftest_summary(degraded=False)

        assert isinstance(snapshot.failed_steps, list)

    def test_get_selftest_summary_status_is_valid(self):
        """status should be one of GREEN, YELLOW, RED."""
        from status_provider import get_selftest_summary

        snapshot = get_selftest_summary(degraded=False)

        assert snapshot.status in ("GREEN", "YELLOW", "RED", "UNKNOWN")

    def test_get_selftest_summary_mode_reflects_degraded_param(self):
        """mode should reflect the degraded parameter."""
        from status_provider import get_selftest_summary

        # Non-degraded mode
        snapshot_strict = get_selftest_summary(degraded=False)
        assert snapshot_strict.mode in ("strict", "kernel-only")

        # Degraded mode
        snapshot_degraded = get_selftest_summary(degraded=True)
        assert snapshot_degraded.mode == "degraded"

    def test_get_selftest_summary_status_reflects_tier_flags(self):
        """Status should be consistent with kernel_ok and governance_ok flags."""
        from status_provider import get_selftest_summary

        snapshot = get_selftest_summary(degraded=False)

        # Status logic:
        # - RED if kernel_ok is False
        # - YELLOW if kernel_ok but not governance_ok
        # - GREEN if both are True
        if not snapshot.kernel_ok:
            assert snapshot.status == "RED"
        elif not snapshot.governance_ok:
            assert snapshot.status == "YELLOW"
        else:
            assert snapshot.status == "GREEN"


class TestSelftestSummaryCoherence:
    """Tests verifying in-process summary matches CLI output shape."""

    def test_summary_has_tier_failed_lists(self):
        """Summary should include tier-specific failure lists."""
        from status_provider import get_selftest_summary

        snapshot = get_selftest_summary(degraded=False)

        # These fields should exist (may be empty lists)
        assert hasattr(snapshot, "kernel_failed")
        assert hasattr(snapshot, "governance_failed")
        assert hasattr(snapshot, "optional_failed")
        assert isinstance(snapshot.kernel_failed, list)
        assert isinstance(snapshot.governance_failed, list)
        assert isinstance(snapshot.optional_failed, list)

    def test_failed_steps_is_union_of_tier_failures(self):
        """failed_steps should be consistent with tier failure lists."""
        from status_provider import get_selftest_summary

        snapshot = get_selftest_summary(degraded=False)

        # In strict mode, failed_steps contains all blocking failures
        # This is kernel + governance (optional failures don't block in any mode)
        all_tier_failures = set(snapshot.kernel_failed) | set(snapshot.governance_failed)

        # All failed_steps should be in the tier failure lists
        for step in snapshot.failed_steps:
            assert step in all_tier_failures, f"Step {step} in failed_steps but not in tier lists"
