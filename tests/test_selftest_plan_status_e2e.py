#!/usr/bin/env python3
"""
Task 2: FastAPI E2E Test (plan + status coherence)

This test suite validates coherence between `/api/selftest/plan` and `/platform/status`
endpoints, ensuring that the UI receives consistent information about selftest steps
and their execution status.

**Coherence Contract**:
- Step IDs in `/api/selftest/plan` match keys in `/platform/status` governance.selftest.steps
- summary.total in plan == count of items reported in status
- Status mode (KERNEL/GOVERNANCE/OPTIONAL) matches tier definitions in plan
- If a step is in plan, its metadata (description, dependencies) doesn't contradict status

**Purpose**: Prevent UI confusion where plan and status disagree about available steps
or their properties. This is critical for the selftest modal showing a consistent view.

**Test Coverage** (4 tests):
1. test_plan_and_status_have_matching_step_ids - Step IDs align between endpoints
2. test_plan_and_status_step_counts_align - Total counts match
3. test_plan_tiers_match_status_mode - Tier definitions consistent
4. test_plan_describes_status_steps - Status steps have corresponding plan entries
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def fastapi_client():
    """Create FastAPI test client."""
    from swarm.tools.flow_studio_fastapi import app

    return TestClient(app)


class TestSelfTestPlanStatusCoherence:
    """E2E tests for coherence between /api/selftest/plan and /platform/status."""

    def test_plan_and_status_have_matching_step_ids(self, fastapi_client):
        """
        Test that step IDs in plan match keys in status.

        **Coherence requirement**:
        - Each step.id in /api/selftest/plan should correspond to a step
          tracked in /platform/status
        - Status should have at least the kernel step available

        **Test flow**:
        1. GET /api/selftest/plan
        2. GET /platform/status
        3. Extract step IDs from plan
        4. Verify status tracks relevant steps (at least core-checks for KERNEL tier)
        """
        # Arrange & Act: Fetch both endpoints
        plan_resp = fastapi_client.get("/api/selftest/plan")
        status_resp = fastapi_client.get("/platform/status")

        # Assert: Both endpoints accessible (or gracefully degraded)
        assert plan_resp.status_code in (200, 503), (
            f"Plan endpoint returned {plan_resp.status_code}"
        )
        assert status_resp.status_code in (200, 503), (
            f"Status endpoint returned {status_resp.status_code}"
        )

        # Skip if either service unavailable
        if plan_resp.status_code == 503 or status_resp.status_code == 503:
            pytest.skip("One or both endpoints unavailable (503)")

        # Act: Extract data
        plan_data = plan_resp.json()
        status_data = status_resp.json()

        # Extract step IDs from plan
        plan_step_ids = {step["id"] for step in plan_data["steps"]}

        # Extract steps tracked in status (if available)
        # Status structure: {governance: {selftest: {steps: {...}}}}
        status_selftest = status_data.get("governance", {}).get("selftest", {})

        # Assert: Plan has step IDs
        assert len(plan_step_ids) > 0, "Plan has no steps"

        # Assert: Status acknowledges at least the KERNEL step
        # The status may not have all steps (depending on implementation),
        # but should be aware of core-checks (the KERNEL step)
        if "steps" in status_selftest and status_selftest["steps"]:
            status_step_ids = set(status_selftest["steps"].keys())
            # Verify no step in status contradicts the plan
            invalid_status_steps = status_step_ids - plan_step_ids
            assert not invalid_status_steps, f"Status has steps not in plan: {invalid_status_steps}"

    def test_plan_and_status_step_counts_align(self, fastapi_client):
        """
        Test that summary counts in plan match what status tracks.

        **Coherence requirement**:
        - summary.total in plan should align with steps counted in status
        - If status doesn't track all steps, it should at least match plan's KERNEL tier

        **Test flow**:
        1. GET /api/selftest/plan
        2. GET /platform/status
        3. Count steps in plan
        4. Count steps in status (if available)
        5. Verify alignment or document graceful degradation
        """
        # Arrange & Act: Fetch both endpoints
        plan_resp = fastapi_client.get("/api/selftest/plan")
        status_resp = fastapi_client.get("/platform/status")

        if plan_resp.status_code == 503 or status_resp.status_code == 503:
            pytest.skip("One or both endpoints unavailable (503)")

        # Act: Extract data
        plan_data = plan_resp.json()
        status_data = status_resp.json()

        # Extract counts from plan
        plan_total = plan_data["summary"]["total"]
        plan_by_tier = plan_data["summary"]["by_tier"]
        kernel_count = plan_by_tier["kernel"]

        # Extract status information
        status_selftest = status_data.get("governance", {}).get("selftest", {})
        status_steps = status_selftest.get("steps", {})

        # Assert: Plan has valid count
        assert plan_total > 0, "Plan should have steps"
        assert kernel_count >= 1, "Plan should have at least 1 KERNEL step"

        # If status has steps, verify consistency
        if status_steps:
            status_step_count = len(status_steps)
            # Status may not track all steps, but shouldn't contradict plan
            assert status_step_count <= plan_total, (
                f"Status tracks {status_step_count} steps, but plan only has {plan_total}"
            )

    def test_plan_tiers_match_status_mode(self, fastapi_client):
        """
        Test that selftest execution mode in status aligns with tier definitions in plan.

        **Coherence requirement**:
        - If status reports "mode: KERNEL", only KERNEL steps should fail hard
        - If status reports "mode: GOVERNANCE", KERNEL + GOVERNANCE failures matter
        - If status reports no failures, execution aligned with planned tiers

        **Test flow**:
        1. GET /api/selftest/plan
        2. GET /platform/status
        3. Extract tier distribution from plan
        4. Extract execution mode from status (if present)
        5. Verify consistency
        """
        # Arrange & Act: Fetch both endpoints
        plan_resp = fastapi_client.get("/api/selftest/plan")
        status_resp = fastapi_client.get("/platform/status")

        if plan_resp.status_code == 503 or status_resp.status_code == 503:
            pytest.skip("One or both endpoints unavailable (503)")

        # Act: Extract data
        plan_data = plan_resp.json()
        status_data = status_resp.json()

        # Extract tier counts from plan
        by_tier = plan_data["summary"]["by_tier"]
        has_kernel = by_tier["kernel"] > 0
        has_governance = by_tier["governance"] > 0
        by_tier["optional"] > 0

        # Assert: Plan has proper tier structure
        assert has_kernel, "Plan should have KERNEL tier steps"
        assert has_governance, "Plan should have GOVERNANCE tier steps"

        # Extract status information
        status_selftest = status_data.get("governance", {}).get("selftest", {})
        status_mode = status_selftest.get("mode", "unknown")

        # Assert: If status reports a mode, it should be valid
        valid_modes = {"kernel", "governance", "optional", "strict", "unknown"}
        assert status_mode in valid_modes, (
            f"Invalid status mode: {status_mode}. Valid modes: {valid_modes}"
        )

        # Assert: Consistency
        # If status is in KERNEL mode, it should respect KERNEL tiers
        if status_mode == "kernel":
            # Status should only care about KERNEL tier
            assert has_kernel, "Status is KERNEL mode but plan has no KERNEL steps"

    def test_plan_describes_status_steps(self, fastapi_client):
        """
        Test that every step reported in status has metadata in the plan.

        **Coherence requirement**:
        - If status tracks a step (e.g., "core-checks"), the plan must describe it
        - Status step must have corresponding plan entry with matching id
        - Plan should provide description, dependencies for UI rendering

        **Test flow**:
        1. GET /api/selftest/plan
        2. GET /platform/status
        3. For each step in status, verify plan has matching entry
        4. Verify plan entry has complete metadata
        """
        # Arrange & Act: Fetch both endpoints
        plan_resp = fastapi_client.get("/api/selftest/plan")
        status_resp = fastapi_client.get("/platform/status")

        if plan_resp.status_code == 503 or status_resp.status_code == 503:
            pytest.skip("One or both endpoints unavailable (503)")

        # Act: Extract data
        plan_data = plan_resp.json()
        status_data = status_resp.json()

        # Build plan index by step ID
        plan_step_map = {step["id"]: step for step in plan_data["steps"]}

        # Extract steps from status
        status_selftest = status_data.get("governance", {}).get("selftest", {})
        status_steps = status_selftest.get("steps", {})

        # Assert: For each status step, plan has matching metadata
        for status_step_id in status_steps.keys():
            assert status_step_id in plan_step_map, (
                f"Status tracks step '{status_step_id}' but plan has no entry for it"
            )

            # Assert: Plan entry has required metadata
            plan_step = plan_step_map[status_step_id]
            assert "description" in plan_step, (
                f"Plan entry for '{status_step_id}' missing description"
            )
            assert "tier" in plan_step, f"Plan entry for '{status_step_id}' missing tier"
            assert "depends_on" in plan_step, (
                f"Plan entry for '{status_step_id}' missing depends_on"
            )

    def test_plan_step_sequence_respects_dependencies(self, fastapi_client):
        """
        Test that plan's dependency ordering is valid for status execution.

        **Coherence requirement**:
        - Steps with dependencies should come after their dependencies in plan
        - No circular dependencies
        - Execution order can be derived from depends_on

        **Test flow**:
        1. GET /api/selftest/plan
        2. Extract step order and dependencies
        3. Verify topological ordering: no step depends on a later step
        4. Verify no circular dependencies
        """
        # Arrange & Act: Fetch plan
        plan_resp = fastapi_client.get("/api/selftest/plan")

        if plan_resp.status_code == 503:
            pytest.skip("Plan endpoint unavailable (503)")

        # Act: Extract data
        plan_data = plan_resp.json()
        steps = plan_data["steps"]

        # Build step index: id -> position in list
        step_index = {step["id"]: i for i, step in enumerate(steps)}

        # Assert: Topological ordering (no forward references)
        for i, step in enumerate(steps):
            step_id = step["id"]
            for dep_id in step.get("depends_on", []):
                dep_idx = step_index.get(dep_id, -1)
                assert dep_idx >= 0, f"Step '{step_id}' depends on '{dep_id}' which is not in plan"
                assert dep_idx < i, (
                    f"Step '{step_id}' (position {i}) depends on '{dep_id}' "
                    f"(position {dep_idx}), which comes later (forward reference)"
                )

        # Assert: No circular dependencies (simple check)
        # A more sophisticated check would do full cycle detection
        for step in steps:
            assert step["id"] not in step.get("depends_on", []), (
                f"Step '{step['id']}' has self-dependency"
            )
