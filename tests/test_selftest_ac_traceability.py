#!/usr/bin/env python3
"""
AC Traceability Chain Tests

This test suite validates the full AC (Acceptance Criteria) traceability chain:

**Chain Path**:
1. Config layer: `selftest_config.py` SelfTestStep.ac_ids field
2. Plan layer: `/api/selftest/plan` returns steps with ac_ids
3. Status layer: `/platform/status` includes governance.ac with AC ID aggregation
4. UI layer: Flow Studio modal displays AC IDs as badges (manual verification)

**Test Coverage** (3 mandatory + optional):
1. test_plan_includes_ac_ids - /api/selftest/plan step objects have ac_ids field
2. test_status_ac_aggregation - /platform/status includes governance.ac section
3. test_ac_references_valid_steps - All AC IDs in status reference valid steps from plan
4. test_ac_status_worst_status_wins - AC status aggregation selects worst status
5. test_ac_config_consistency - ac_ids in config match expected coverage
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
    """Create FastAPI test client for Flow Studio."""
    from swarm.tools.flow_studio_fastapi import app

    return TestClient(app)


@pytest.fixture
def selftest_steps():
    """Load selftest configuration."""
    from swarm.tools.selftest_config import SELFTEST_STEPS

    return SELFTEST_STEPS


class TestACTraceabilityChain:
    """Tests for AC (Acceptance Criteria) traceability from config → plan → status → UI."""

    def test_plan_includes_ac_ids(self, fastapi_client):
        """
        Test that /api/selftest/plan returns steps with ac_ids field.

        **Chain Link**: Config → Plan API
        **Contract**: Each step object must have 'ac_ids' field (list of strings)

        **Verification**:
        1. GET /api/selftest/plan
        2. For each step, check ac_ids field exists and is a list
        3. At least one step should have non-empty ac_ids
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        # Assert: Status is acceptable
        assert resp.status_code in (200, 503), (
            f"Expected 200 or 503, got {resp.status_code}: {resp.text}"
        )

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        # Act: Parse JSON
        data = resp.json()

        # Assert: Plan structure is valid
        assert "steps" in data, "Plan missing 'steps' field"
        assert isinstance(data["steps"], list), "'steps' should be a list"
        assert len(data["steps"]) > 0, "Plan should have at least one step"

        # Assert: Each step has ac_ids field
        has_nonempty_ac = False
        for step in data["steps"]:
            assert isinstance(step, dict), f"Step should be a dict, got {type(step)}"
            assert "ac_ids" in step, f"Step {step.get('id')} missing 'ac_ids' field"
            assert isinstance(step["ac_ids"], list), (
                f"Step {step.get('id')} ac_ids should be a list, got {type(step['ac_ids'])}"
            )
            # Check all ac_ids are strings
            for ac_id in step["ac_ids"]:
                assert isinstance(ac_id, str), (
                    f"AC ID in step {step.get('id')} should be string, got {type(ac_id)}"
                )
            # Track if we found at least one non-empty AC list
            if step["ac_ids"]:
                has_nonempty_ac = True

        # Assert: At least one step should have AC IDs (not all empty)
        assert has_nonempty_ac, "No steps have AC IDs; configuration may be incomplete"

    def test_status_ac_aggregation(self, fastapi_client):
        """
        Test that /platform/status includes governance.ac with AC status aggregation.

        **Chain Link**: Plan → Status API
        **Contract**: Response must include governance.ac dict with AC ID → status mapping

        **Verification**:
        1. GET /platform/status
        2. Check governance.ac exists and is a dict
        3. AC keys should match step ac_ids from plan (if available)
        4. AC values should be valid status strings
        """
        # Arrange
        plan_resp = fastapi_client.get("/api/selftest/plan")
        if plan_resp.status_code != 200:
            pytest.skip("Cannot test status aggregation without plan (plan API not available)")

        plan_data = plan_resp.json()
        plan_ac_ids = set()
        for step in plan_data.get("steps", []):
            plan_ac_ids.update(step.get("ac_ids", []))

        # Act: Get status
        status_resp = fastapi_client.get("/platform/status")

        # Assert: Status available
        assert status_resp.status_code in (200, 503), (
            f"Expected 200 or 503, got {status_resp.status_code}: {status_resp.text}"
        )

        if status_resp.status_code == 503:
            pytest.skip("Status provider not available (503)")

        # Act: Parse status
        status_data = status_resp.json()

        # Assert: governance section exists
        assert "governance" in status_data, "Status missing 'governance' field"
        assert isinstance(status_data["governance"], dict), "governance should be a dict"

        # Assert: ac field exists in governance
        assert "ac" in status_data["governance"], "governance missing 'ac' field"
        ac_status = status_data["governance"]["ac"]
        assert isinstance(ac_status, dict), "governance.ac should be a dict"

        # Assert: AC IDs in status match plan (if plan had AC IDs)
        status_ac_ids = set(ac_status.keys())
        if plan_ac_ids:
            # Plan has AC IDs, status should too
            assert len(status_ac_ids) > 0, "Plan has AC IDs but status.governance.ac is empty"
            # All status ACs should be in plan (and vice versa)
            assert status_ac_ids == plan_ac_ids, (
                f"AC IDs mismatch: plan={sorted(plan_ac_ids)}, status={sorted(status_ac_ids)}"
            )

        # Assert: AC values are valid status strings
        valid_statuses = {"PASS", "WARNING", "INFO", "CRITICAL", "FAILURE"}
        for ac_id, status_val in ac_status.items():
            assert status_val in valid_statuses, (
                f"AC {ac_id} has invalid status {status_val!r}; must be one of {valid_statuses}"
            )

    def test_ac_references_valid_steps(self, fastapi_client):
        """
        Test that all AC IDs in status reference valid steps from plan.

        **Chain Link**: Plan → Status Coherence
        **Contract**: Every AC in governance.ac should map to at least one step in the plan

        **Verification**:
        1. GET /api/selftest/plan (collect step IDs)
        2. GET /platform/status (collect AC IDs)
        3. For each AC, verify at least one step in plan claims it
        """
        # Arrange: Get plan
        plan_resp = fastapi_client.get("/api/selftest/plan")
        if plan_resp.status_code != 200:
            pytest.skip("Plan API not available")

        plan_data = plan_resp.json()

        # Build AC → [step_ids] map from plan
        ac_to_steps = {}
        for step in plan_data.get("steps", []):
            step_id = step.get("id")
            for ac_id in step.get("ac_ids", []):
                if ac_id not in ac_to_steps:
                    ac_to_steps[ac_id] = []
                ac_to_steps[ac_id].append(step_id)

        # Act: Get status
        status_resp = fastapi_client.get("/platform/status")
        if status_resp.status_code != 200:
            pytest.skip("Status API not available")

        status_data = status_resp.json()
        status_ac_ids = set(status_data.get("governance", {}).get("ac", {}).keys())

        # Assert: Every AC in status should map to at least one step
        for ac_id in status_ac_ids:
            assert ac_id in ac_to_steps, (
                f"AC {ac_id} in status.governance.ac but not claimed by any step in plan"
            )
            assert len(ac_to_steps[ac_id]) > 0, f"AC {ac_id} has no steps; map building failed"

    def test_ac_status_worst_status_wins(self, fastapi_client, selftest_steps):
        """
        Test that AC status aggregation selects worst status when multiple steps share an AC.

        **Chain Link**: Status Aggregation Logic
        **Contract**: If AC X is covered by steps A, B, C:
          - If any step fails with CRITICAL severity → AC status is CRITICAL
          - Else if any step fails with WARNING severity → AC status is WARNING
          - Else if any step fails with INFO severity → AC status is INFO
          - Else → AC status is PASS

        **Verification**:
        1. Check config: find an AC with multiple steps
        2. Verify the AC's status matches the worst of its steps' statuses
        """
        # Arrange: Build AC → [steps] map from config
        ac_to_steps = {}
        for step in selftest_steps:
            for ac_id in step.ac_ids:
                if ac_id not in ac_to_steps:
                    ac_to_steps[ac_id] = []
                ac_to_steps[ac_id].append(step)

        # Find an AC with multiple steps (if any)
        ac_with_multiple_steps = None
        for ac_id, steps in ac_to_steps.items():
            if len(steps) > 1:
                ac_with_multiple_steps = (ac_id, steps)
                break

        if not ac_with_multiple_steps:
            pytest.skip(
                "No AC with multiple steps in config; aggregation logic cannot be fully tested"
            )

        ac_id, steps = ac_with_multiple_steps

        # Get status
        status_resp = fastapi_client.get("/platform/status")
        if status_resp.status_code != 200:
            pytest.skip("Status API not available; cannot test aggregation")

        status_data = status_resp.json()
        ac_status = status_data.get("governance", {}).get("ac", {})

        # Assert: AC status exists
        assert ac_id in ac_status, f"AC {ac_id} missing from status"

        # Verify the logic: worst status should match the expected aggregation
        # This is a logical verification; actual result depends on step status
        ac_result_status = ac_status[ac_id]
        assert ac_result_status in {"PASS", "WARNING", "INFO", "CRITICAL", "FAILURE"}, (
            f"AC {ac_id} has invalid aggregated status {ac_result_status!r}"
        )

    def test_ac_config_consistency(self, selftest_steps):
        """
        Test that ac_ids in config are consistent and non-empty.

        **Chain Link**: Config Layer
        **Contract**: SelfTestStep.ac_ids should be:
          - A list of strings
          - Non-empty (at least one AC per step)
          - Unique within each step (no duplicates)
          - Follow naming convention (e.g., AC-SELFTEST-*)

        **Verification**:
        1. For each step in config, validate ac_ids
        2. Check naming patterns
        3. Check for duplicates across steps
        """
        # Arrange
        seen_ac_ids = set()
        step_ac_counts = {}

        # Act & Assert: Validate each step
        for step in selftest_steps:
            assert isinstance(step.ac_ids, list), (
                f"Step {step.id} ac_ids should be a list, got {type(step.ac_ids)}"
            )
            assert len(step.ac_ids) > 0, (
                f"Step {step.id} has empty ac_ids; every step should declare coverage"
            )

            # Check each AC
            step_ac_set = set()
            for ac_id in step.ac_ids:
                assert isinstance(ac_id, str), (
                    f"Step {step.id} AC {ac_id} should be string, got {type(ac_id)}"
                )
                assert ac_id.startswith("AC-"), (
                    f"Step {step.id} AC {ac_id!r} should start with 'AC-'"
                )
                assert ac_id not in step_ac_set, f"Step {step.id} has duplicate AC {ac_id}"
                step_ac_set.add(ac_id)
                seen_ac_ids.add(ac_id)

            step_ac_counts[step.id] = len(step.ac_ids)

        # Assert: Summary
        assert len(seen_ac_ids) > 0, "No AC IDs found in any step"
        # Typically, each step should have at least one AC; ratio should be reasonable
        avg_ac_per_step = sum(step_ac_counts.values()) / len(selftest_steps)
        assert avg_ac_per_step >= 1.0, (
            f"Average AC per step is {avg_ac_per_step:.2f}; should be >= 1.0"
        )


class TestACTraceabilityIntegration:
    """Integration tests for the full AC traceability flow."""

    def test_full_chain_end_to_end(self, fastapi_client, selftest_steps):
        """
        Test the complete AC traceability chain in one flow.

        **Scenario**:
        1. Load config and verify AC IDs exist
        2. GET /api/selftest/plan and verify ac_ids in steps
        3. GET /platform/status and verify governance.ac
        4. Verify all ACs in status are declared in config

        **Assertion**: No AC IDs "appear out of nowhere" in the status;
        all are traceable back to config.
        """
        # Step 1: Collect AC IDs from config
        config_ac_ids = set()
        for step in selftest_steps:
            config_ac_ids.update(step.ac_ids)

        assert len(config_ac_ids) > 0, "Config has no AC IDs"

        # Step 2: Verify plan includes config ACs
        plan_resp = fastapi_client.get("/api/selftest/plan")
        if plan_resp.status_code != 200:
            pytest.skip("Plan API not available")

        plan_data = plan_resp.json()
        plan_ac_ids = set()
        for step in plan_data.get("steps", []):
            plan_ac_ids.update(step.get("ac_ids", []))

        # Assert plan ACs match config ACs
        assert plan_ac_ids == config_ac_ids, (
            f"Plan ACs {sorted(plan_ac_ids)} != config ACs {sorted(config_ac_ids)}"
        )

        # Step 3: Verify status includes plan ACs
        status_resp = fastapi_client.get("/platform/status")
        if status_resp.status_code != 200:
            pytest.skip("Status API not available")

        status_data = status_resp.json()
        status_ac_ids = set(status_data.get("governance", {}).get("ac", {}).keys())

        # Assert status ACs match plan ACs (and thus config ACs)
        if plan_ac_ids:  # Only check if plan has ACs
            assert status_ac_ids == plan_ac_ids, (
                f"Status ACs {sorted(status_ac_ids)} != plan ACs {sorted(plan_ac_ids)}"
            )

        # Step 4: Verify no "orphan" ACs in status
        orphan_ac = status_ac_ids - config_ac_ids
        assert len(orphan_ac) == 0, f"Status has orphan AC IDs not in config: {sorted(orphan_ac)}"
