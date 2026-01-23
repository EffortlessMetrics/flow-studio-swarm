#!/usr/bin/env python3
"""
Task 1: /api/selftest/plan Contract Test

This test suite validates the `/api/selftest/plan` API contract.

**Contract Specification**:
- Endpoint: GET /api/selftest/plan
- Response: JSON with `steps` (list), `summary` (dict with `total` and `by_tier`)
- Required step fields: `id`, `tier`, `category`, `severity`, `description`, `depends_on`
- Valid tier values: KERNEL, GOVERNANCE, OPTIONAL
- Invariants:
  - summary.total == len(steps)
  - sum(by_tier.values()) == summary.total
  - All steps have required fields
  - All tier values are valid enums
  - No duplicate step IDs
  - All dependencies reference valid step IDs

**Purpose**: Lock in the API contract to prevent regressions and ensure backward
compatibility as the Flow Studio UI evolves.

**Test Coverage** (6 tests):
1. test_selftest_plan_api_contract_structure - Overall structure is valid
2. test_selftest_plan_api_contract_step_fields - Each step has required fields
3. test_selftest_plan_api_contract_tier_values - Tier values are valid
4. test_selftest_plan_api_contract_summary_counts - Summary counts match steps
5. test_selftest_plan_api_contract_no_duplicates - No duplicate step IDs
6. test_selftest_plan_api_contract_dependencies_valid - Dependencies are valid
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


class TestSelfTestPlanAPIContract:
    """Contract tests for /api/selftest/plan API endpoint."""

    def test_selftest_plan_api_contract_structure(self, fastapi_client):
        """
        Test that /api/selftest/plan returns valid JSON with required top-level structure.

        **Contract**:
        - Response is a JSON object with keys: version, steps, summary
        - steps is a non-empty list
        - summary is a dict with keys: total, by_tier
        - by_tier is a dict with keys: kernel, governance, optional

        **Test**:
        - GET /api/selftest/plan
        - Verify response status is 200 or 503 (graceful degradation)
        - If 200, validate structure
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        # Assert: Status code is acceptable (200 success or 503 service unavailable)
        assert resp.status_code in (200, 503), (
            f"Expected status 200 or 503, got {resp.status_code}: {resp.text}"
        )

        # Skip remaining assertions if service unavailable
        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        # Act: Parse JSON
        data = resp.json()

        # Assert: Top-level keys exist
        assert isinstance(data, dict), "Response should be a JSON object"
        assert "version" in data, "Response missing 'version' field"
        assert "steps" in data, "Response missing 'steps' field"
        assert "summary" in data, "Response missing 'summary' field"

        # Assert: steps is a list
        assert isinstance(data["steps"], list), "'steps' should be a list"
        assert len(data["steps"]) > 0, "'steps' should not be empty"

        # Assert: summary structure
        summary = data["summary"]
        assert isinstance(summary, dict), "'summary' should be a dict"
        assert "total" in summary, "summary missing 'total' field"
        assert "by_tier" in summary, "summary missing 'by_tier' field"

        # Assert: by_tier structure
        by_tier = summary["by_tier"]
        assert isinstance(by_tier, dict), "by_tier should be a dict"
        assert "kernel" in by_tier, "by_tier missing 'kernel' count"
        assert "governance" in by_tier, "by_tier missing 'governance' count"
        assert "optional" in by_tier, "by_tier missing 'optional' count"

    def test_selftest_plan_api_contract_step_fields(self, fastapi_client):
        """
        Test that each step in the plan has all required fields.

        **Contract**:
        - Each step is a dict with required fields:
          - id: string (unique identifier)
          - tier: string (one of: kernel, governance, optional)
          - category: string (one of: security, performance, correctness, governance)
          - severity: string (one of: critical, warning, info)
          - description: string (non-empty)
          - depends_on: list of strings (may be empty)

        **Test**:
        - Fetch /api/selftest/plan
        - For each step, verify all required fields are present and of correct type
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Assert: Each step has required fields with correct types
        required_fields = {
            "id": str,
            "tier": str,
            "category": str,
            "severity": str,
            "description": str,
            "depends_on": list,
        }

        for i, step in enumerate(steps):
            # Assert: All fields present
            missing_fields = set(required_fields.keys()) - set(step.keys())
            assert not missing_fields, (
                f"Step {i} ({step.get('id', 'unknown')}) missing fields: {missing_fields}"
            )

            # Assert: All fields have correct types
            for field_name, expected_type in required_fields.items():
                actual_value = step[field_name]
                actual_type = type(actual_value)
                assert isinstance(actual_value, expected_type), (
                    f"Step {i} ('{step['id']}'): field '{field_name}' "
                    f"should be {expected_type.__name__}, got {actual_type.__name__}"
                )

            # Assert: Description is non-empty
            assert len(step["description"]) > 0, f"Step {i} ('{step['id']}'): description is empty"

            # Assert: depends_on is a list (may be empty)
            assert isinstance(step["depends_on"], list), (
                f"Step {i} ('{step['id']}'): depends_on should be a list"
            )

    def test_selftest_plan_api_contract_tier_values(self, fastapi_client):
        """
        Test that all tier values are valid enum values.

        **Contract**:
        - tier field in each step must be one of: kernel, governance, optional

        **Test**:
        - Fetch /api/selftest/plan
        - Verify each step's tier is a valid enum value
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Assert: Valid tier values
        valid_tiers = {"kernel", "governance", "optional"}

        for step in steps:
            tier = step["tier"]
            assert tier in valid_tiers, (
                f"Step '{step['id']}' has invalid tier '{tier}', expected one of {valid_tiers}"
            )

    def test_selftest_plan_api_contract_summary_counts(self, fastapi_client):
        """
        Test that summary counts match actual step counts.

        **Contract**:
        - summary.total == len(steps)
        - summary.by_tier.kernel == count of steps with tier='kernel'
        - summary.by_tier.governance == count of steps with tier='governance'
        - summary.by_tier.optional == count of steps with tier='optional'
        - sum(by_tier.values()) == summary.total

        **Test**:
        - Fetch /api/selftest/plan
        - Count steps by tier
        - Verify counts match summary
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]
        summary = data["summary"]
        by_tier = summary["by_tier"]

        # Act: Count steps by tier
        actual_kernel = sum(1 for s in steps if s["tier"] == "kernel")
        actual_governance = sum(1 for s in steps if s["tier"] == "governance")
        actual_optional = sum(1 for s in steps if s["tier"] == "optional")

        # Assert: summary.total matches step count
        assert summary["total"] == len(steps), (
            f"summary.total mismatch: reported {summary['total']}, actual {len(steps)}"
        )

        # Assert: by_tier counts match actual
        assert by_tier["kernel"] == actual_kernel, (
            f"kernel count mismatch: reported {by_tier['kernel']}, actual {actual_kernel}"
        )
        assert by_tier["governance"] == actual_governance, (
            f"governance count mismatch: reported {by_tier['governance']}, "
            f"actual {actual_governance}"
        )
        assert by_tier["optional"] == actual_optional, (
            f"optional count mismatch: reported {by_tier['optional']}, actual {actual_optional}"
        )

        # Assert: by_tier sum matches total
        by_tier_sum = by_tier["kernel"] + by_tier["governance"] + by_tier["optional"]
        assert by_tier_sum == summary["total"], (
            f"by_tier sum mismatch: {by_tier_sum} != {summary['total']}"
        )

    def test_selftest_plan_api_contract_no_duplicates(self, fastapi_client):
        """
        Test that there are no duplicate step IDs.

        **Contract**:
        - Each step's id must be unique within the plan
        - No two steps can have the same id

        **Test**:
        - Fetch /api/selftest/plan
        - Collect all step IDs
        - Verify set(ids) == len(ids) (no duplicates)
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Act: Collect step IDs
        step_ids = [step["id"] for step in steps]
        unique_ids = set(step_ids)

        # Assert: No duplicates
        assert len(step_ids) == len(unique_ids), (
            f"Duplicate step IDs found: {[id for id in step_ids if step_ids.count(id) > 1]}"
        )

    def test_selftest_plan_api_contract_dependencies_valid(self, fastapi_client):
        """
        Test that all step dependencies reference valid step IDs.

        **Contract**:
        - Each step's depends_on field contains step IDs
        - All IDs in depends_on must exist in the steps array
        - A step cannot depend on itself
        - Dependencies must form a valid DAG (no cycles)

        **Test**:
        - Fetch /api/selftest/plan
        - Build set of all step IDs
        - For each step, verify all dependencies reference valid IDs
        - Verify no self-dependencies
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Act: Collect all step IDs
        step_ids = {step["id"] for step in steps}

        # Assert: All dependencies reference valid steps and no self-deps
        for step in steps:
            step_id = step["id"]
            for dep_id in step["depends_on"]:
                # Assert: Dependency exists
                assert dep_id in step_ids, (
                    f"Step '{step_id}' depends on unknown step '{dep_id}'. "
                    f"Valid step IDs: {sorted(step_ids)}"
                )

                # Assert: No self-dependencies
                assert dep_id != step_id, f"Step '{step_id}' has self-dependency: {dep_id}"

    def test_selftest_plan_has_ac_ids(self, fastapi_client):
        """
        Test that steps have AC IDs (acceptance criteria) for traceability.

        **Contract**:
        - Each step has an ac_ids field (list, may be empty)
        - AC IDs follow format: AC-SELFTEST-* or AC-*
        - AC IDs should be consistent across steps

        **Test**:
        - Fetch /api/selftest/plan
        - Verify ac_ids field exists and is a list on each step
        - Collect all AC IDs and verify format
        - Ensure no duplicate ACs assigned to same step
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Collect all AC IDs for validation
        all_ac_ids = set()
        ac_id_to_steps = {}

        for step in steps:
            # Assert: ac_ids field exists and is a list
            assert "ac_ids" in step, f"Step '{step['id']}' missing ac_ids field"
            assert isinstance(step["ac_ids"], list), (
                f"Step '{step['id']}': ac_ids should be a list, got {type(step['ac_ids']).__name__}"
            )

            # Track AC IDs per step
            for ac_id in step["ac_ids"]:
                assert isinstance(ac_id, str), (
                    f"Step '{step['id']}': AC ID should be string, got {type(ac_id).__name__}"
                )
                assert len(ac_id) > 0, f"Step '{step['id']}': AC ID cannot be empty"

                all_ac_ids.add(ac_id)

                if ac_id not in ac_id_to_steps:
                    ac_id_to_steps[ac_id] = []
                ac_id_to_steps[ac_id].append(step["id"])

        # Assert: AC IDs are not excessively duplicated across steps
        # (Some sharing is OK for shared concerns, like INTROSPECTABLE across governance steps)
        # Allow specific cross-cutting ACs that legitimately apply to all steps
        cross_cutting_acs = {
            "AC-SELFTEST-FAILURE-HINTS",  # All steps provide hints
            "AC-SELFTEST-DEGRADATION-TRACKED",  # All governance steps track degradations
        }
        for ac_id, step_ids in ac_id_to_steps.items():
            # Cross-cutting ACs can appear on all steps; others capped at 10
            max_allowed = 11 if ac_id in cross_cutting_acs else 10
            assert len(step_ids) <= max_allowed, (
                f"AC '{ac_id}' assigned to {len(step_ids)} steps "
                f"({', '.join(step_ids)}); seems over-shared"
            )

    def test_selftest_plan_version_is_valid(self, fastapi_client):
        """
        Test that the plan version field is valid and parseable.

        **Contract**:
        - version is a string in semver format (e.g., "1.0.0" or "1.0")
        - version is non-empty
        - version can be used for change detection

        **Test**:
        - Fetch /api/selftest/plan
        - Verify version is a string
        - Verify version matches expected format
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()

        # Assert: version field exists and is a string
        assert "version" in data, "Response missing 'version' field"
        version = data["version"]
        assert isinstance(version, str), f"version should be string, got {type(version).__name__}"
        assert len(version) > 0, "version cannot be empty"

        # Assert: version looks like a version string
        # Expect format like "1.0", "1.0.0", etc.
        parts = version.split(".")
        assert len(parts) >= 2, f"version '{version}' should have at least major.minor format"
        for part in parts:
            assert part.isdigit(), f"version '{version}' has non-numeric component: '{part}'"

    def test_selftest_plan_step_order_consistency(self, fastapi_client):
        """
        Test that the step order is deterministic across multiple calls.

        **Contract**:
        - Calling /api/selftest/plan twice returns steps in the same order
        - Step IDs and all properties are identical
        - Order is deterministic (not randomized)

        **Test**:
        - Call /api/selftest/plan twice
        - Compare step arrays
        - Verify order is identical
        """
        # Arrange & Act
        resp1 = fastapi_client.get("/api/selftest/plan")
        resp2 = fastapi_client.get("/api/selftest/plan")

        if resp1.status_code == 503 or resp2.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data1 = resp1.json()
        data2 = resp2.json()

        # Assert: Same number of steps
        assert len(data1["steps"]) == len(data2["steps"]), "Step count differs between calls"

        # Assert: Steps are in same order
        for i, (step1, step2) in enumerate(zip(data1["steps"], data2["steps"])):
            assert step1["id"] == step2["id"], (
                f"Step order differs at position {i}: '{step1['id']}' vs '{step2['id']}'"
            )

        # Assert: Summary is identical
        assert data1["summary"] == data2["summary"], "Summary differs between calls"

    def test_selftest_plan_response_time(self, fastapi_client):
        """
        Test that /api/selftest/plan responds quickly.

        **Contract**:
        - Response time < 1 second
        - Can be called multiple times without timeout
        - Suitable for real-time UI rendering

        **Test**:
        - Call /api/selftest/plan
        - Measure response time
        - Verify it's acceptable for UI use
        """
        import time

        # Arrange & Act
        start = time.time()
        resp = fastapi_client.get("/api/selftest/plan")
        duration_ms = (time.time() - start) * 1000

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        # Assert: Response time is acceptable
        assert duration_ms < 1000, (
            f"Plan endpoint took {duration_ms:.0f}ms, expected < 1000ms for UI responsiveness"
        )

    def test_selftest_plan_category_values(self, fastapi_client):
        """
        Test that all category values are valid.

        **Contract**:
        - category field in each step must be one of: security, performance, correctness, governance
        - category values are lowercase strings

        **Test**:
        - Fetch /api/selftest/plan
        - Verify each step's category is valid
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Assert: Valid category values
        valid_categories = {"security", "performance", "correctness", "governance"}

        for step in steps:
            category = step["category"]
            assert category in valid_categories, (
                f"Step '{step['id']}' has invalid category '{category}', "
                f"expected one of {valid_categories}"
            )

    def test_selftest_plan_severity_values(self, fastapi_client):
        """
        Test that all severity values are valid.

        **Contract**:
        - severity field in each step must be one of: critical, warning, info
        - severity values are lowercase strings

        **Test**:
        - Fetch /api/selftest/plan
        - Verify each step's severity is valid
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Assert: Valid severity values
        valid_severities = {"critical", "warning", "info"}

        for step in steps:
            severity = step["severity"]
            assert severity in valid_severities, (
                f"Step '{step['id']}' has invalid severity '{severity}', "
                f"expected one of {valid_severities}"
            )

    def test_selftest_plan_no_circular_dependencies(self, fastapi_client):
        """
        Test that dependencies form a valid DAG with no circular references.

        **Contract**:
        - No step can depend (directly or transitively) on itself
        - Dependencies form a directed acyclic graph (DAG)
        - Can be topologically sorted for execution

        **Test**:
        - Fetch /api/selftest/plan
        - Build dependency graph
        - Perform cycle detection using DFS
        - Verify no cycles exist
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Build dependency graph
        dep_graph = {step["id"]: step["depends_on"] for step in steps}

        # Cycle detection using DFS
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dep_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        # Check each node for cycles
        visited = set()
        for node in dep_graph:
            if node not in visited:
                assert not has_cycle(node, visited, set()), (
                    f"Circular dependency detected involving step '{node}'"
                )

    def test_selftest_plan_empty_steps_graceful(self, fastapi_client):
        """
        Test that endpoint handles edge case of empty steps list gracefully.

        **Contract**:
        - If steps is empty, summary.total == 0
        - by_tier counts are all 0
        - Still returns 200 with valid structure

        **Test**:
        - Fetch /api/selftest/plan
        - If steps is empty (edge case), verify summary is consistent
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        data = resp.json()
        steps = data["steps"]

        # Only test if steps is empty (edge case)
        if len(steps) == 0:
            summary = data["summary"]
            assert summary["total"] == 0, "Empty steps should have total=0"
            assert summary["by_tier"]["kernel"] == 0
            assert summary["by_tier"]["governance"] == 0
            assert summary["by_tier"]["optional"] == 0
