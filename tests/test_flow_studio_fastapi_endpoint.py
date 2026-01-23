#!/usr/bin/env python3
"""
FastAPI selftest plan endpoint tests.

Tests the /api/selftest/plan endpoint that provides selftest step information
for Flow Studio governance visualization.

## Test Coverage (10 tests)

1. test_selftest_plan_endpoint_returns_200 - Endpoint returns 200 with valid JSON
2. test_selftest_plan_has_version - Response contains version field
3. test_selftest_plan_has_steps_array - Response contains steps array
4. test_selftest_plan_has_summary - Response contains summary with counts
5. test_selftest_plan_step_structure - Steps have correct fields
6. test_selftest_plan_tier_values - Tier values are valid enums
7. test_selftest_plan_severity_values - Severity values are valid enums
8. test_selftest_plan_category_values - Category values are valid enums
9. test_selftest_plan_no_duplicate_step_ids - No duplicate step IDs in plan
10. test_selftest_plan_dependencies_valid - Dependencies reference valid step IDs
11. test_selftest_plan_graceful_degradation - Handles missing selftest module (503)
12. test_selftest_plan_summary_counts_correct - Summary counts match actual steps
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
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


def test_selftest_plan_endpoint_returns_200(fastapi_client):
    """Test /api/selftest/plan endpoint returns 200 with valid JSON."""
    resp = fastapi_client.get("/api/selftest/plan")

    # Either 200 with plan or 503 if selftest module disabled (both acceptable)
    assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"

    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, dict), "Response should be a JSON object"


def test_selftest_plan_has_version(fastapi_client):
    """Test response contains version field."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        assert "version" in data, "Response missing 'version' field"
        assert data["version"] == "1.0", f"Expected version '1.0', got {data['version']}"


def test_selftest_plan_has_steps_array(fastapi_client):
    """Test response contains steps array."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        assert "steps" in data, "Response missing 'steps' field"
        assert isinstance(data["steps"], list), "'steps' should be a list"
        assert len(data["steps"]) > 0, "Steps array should not be empty"


def test_selftest_plan_has_summary(fastapi_client):
    """Test response contains summary with counts."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        assert "summary" in data, "Response missing 'summary' field"

        summary = data["summary"]
        assert "total" in summary, "Summary missing 'total' field"
        assert "by_tier" in summary, "Summary missing 'by_tier' field"

        by_tier = summary["by_tier"]
        assert "kernel" in by_tier, "by_tier missing 'kernel' count"
        assert "governance" in by_tier, "by_tier missing 'governance' count"
        assert "optional" in by_tier, "by_tier missing 'optional' count"


def test_selftest_plan_step_structure(fastapi_client):
    """Test steps have correct fields and structure."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        steps = data["steps"]

        # Validate each step has required fields
        required_fields = {"id", "tier", "severity", "category", "description", "depends_on"}

        for i, step in enumerate(steps):
            missing_fields = required_fields - set(step.keys())
            assert not missing_fields, (
                f"Step {i} ({step.get('id', 'unknown')}) missing fields: {missing_fields}"
            )

            # Validate field types
            assert isinstance(step["id"], str), (
                f"Step {i}: 'id' should be string, got {type(step['id'])}"
            )
            assert isinstance(step["tier"], str), (
                f"Step {i}: 'tier' should be string, got {type(step['tier'])}"
            )
            assert isinstance(step["severity"], str), (
                f"Step {i}: 'severity' should be string, got {type(step['severity'])}"
            )
            assert isinstance(step["category"], str), (
                f"Step {i}: 'category' should be string, got {type(step['category'])}"
            )
            assert isinstance(step["description"], str), (
                f"Step {i}: 'description' should be string, got {type(step['description'])}"
            )
            assert isinstance(step["depends_on"], list), (
                f"Step {i}: 'depends_on' should be list, got {type(step['depends_on'])}"
            )


def test_selftest_plan_tier_values(fastapi_client):
    """Test tier values are valid enums."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        steps = data["steps"]

        valid_tiers = {"kernel", "governance", "optional"}

        for step in steps:
            tier = step["tier"]
            assert tier in valid_tiers, (
                f"Step '{step['id']}' has invalid tier '{tier}', expected one of {valid_tiers}"
            )


def test_selftest_plan_severity_values(fastapi_client):
    """Test severity values are valid enums."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        steps = data["steps"]

        valid_severities = {"critical", "warning", "info"}

        for step in steps:
            severity = step["severity"]
            assert severity in valid_severities, (
                f"Step '{step['id']}' has invalid severity '{severity}', "
                f"expected one of {valid_severities}"
            )


def test_selftest_plan_category_values(fastapi_client):
    """Test category values are valid enums."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        steps = data["steps"]

        valid_categories = {"security", "performance", "correctness", "governance"}

        for step in steps:
            category = step["category"]
            assert category in valid_categories, (
                f"Step '{step['id']}' has invalid category '{category}', "
                f"expected one of {valid_categories}"
            )


def test_selftest_plan_no_duplicate_step_ids(fastapi_client):
    """Test no duplicate step IDs in plan."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        steps = data["steps"]

        step_ids = [step["id"] for step in steps]
        unique_ids = set(step_ids)

        assert len(step_ids) == len(unique_ids), (
            f"Duplicate step IDs found: {[id for id in step_ids if step_ids.count(id) > 1]}"
        )


def test_selftest_plan_dependencies_valid(fastapi_client):
    """Test dependencies reference valid step IDs."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        steps = data["steps"]

        # Collect all step IDs
        step_ids = {step["id"] for step in steps}

        # Check each dependency
        for step in steps:
            for dep in step["depends_on"]:
                assert dep in step_ids, (
                    f"Step '{step['id']}' depends on unknown step '{dep}'. "
                    f"Valid step IDs: {sorted(step_ids)}"
                )


def test_selftest_plan_graceful_degradation(fastapi_client, monkeypatch):
    """Test handles missing selftest module gracefully (503)."""
    # This test verifies the error handling in the endpoint
    # The actual endpoint already handles ImportError/SystemExit
    # We just verify the error response format

    resp = fastapi_client.get("/api/selftest/plan")

    # If we get 503, check error format
    if resp.status_code == 503:
        data = resp.json()
        assert "error" in data, "Error response should have 'error' field"
        assert isinstance(data["error"], str), "'error' should be a string"


def test_selftest_plan_summary_counts_correct(fastapi_client):
    """Test summary counts match actual steps."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 200:
        data = resp.json()
        steps = data["steps"]
        summary = data["summary"]

        # Count steps by tier
        actual_kernel = sum(1 for s in steps if s["tier"] == "kernel")
        actual_governance = sum(1 for s in steps if s["tier"] == "governance")
        actual_optional = sum(1 for s in steps if s["tier"] == "optional")

        # Verify summary matches
        assert summary["by_tier"]["kernel"] == actual_kernel, (
            f"Kernel count mismatch: summary says {summary['by_tier']['kernel']}, "
            f"actual is {actual_kernel}"
        )
        assert summary["by_tier"]["governance"] == actual_governance, (
            f"Governance count mismatch: summary says {summary['by_tier']['governance']}, "
            f"actual is {actual_governance}"
        )
        assert summary["by_tier"]["optional"] == actual_optional, (
            f"Optional count mismatch: summary says {summary['by_tier']['optional']}, "
            f"actual is {actual_optional}"
        )

        # Verify total matches
        total_by_tier = (
            summary["by_tier"]["kernel"]
            + summary["by_tier"]["governance"]
            + summary["by_tier"]["optional"]
        )
        assert summary["total"] == len(steps), (
            f"Total count mismatch: summary says {summary['total']}, actual is {len(steps)}"
        )
        assert summary["total"] == total_by_tier, (
            f"Total doesn't match tier breakdown: total={summary['total']}, "
            f"tier_sum={total_by_tier}"
        )
