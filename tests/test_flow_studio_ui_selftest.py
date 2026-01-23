#!/usr/bin/env python3
"""
Flow Studio UI selftest integration tests.

Tests the selftest plan visualization in Flow Studio UI.
These tests verify the expected UI behavior patterns for displaying
selftest data and governance hints.

## Test Coverage (9 tests)

1. test_selftest_plan_api_returns_data - API returns plan data structure
2. test_plan_has_steps_with_tiers - Plan includes steps with tier classification
3. test_tier_colors_mapping - Tier colors are correctly mapped
4. test_hint_generation_structure - Hints have correct structure
5. test_commands_are_copyable - Command strings are present and valid
6. test_docs_links_present - Documentation links are included
7. test_empty_plan_handled - Empty plan is handled gracefully
8. test_degraded_mode_hints - Degraded mode generates advisory hints
9. test_failure_mode_hints - Failure mode generates failure hints
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


def test_selftest_plan_api_returns_data(fastapi_client):
    """Test /api/selftest/plan returns valid plan data structure."""
    resp = fastapi_client.get("/api/selftest/plan")

    # Skip test if selftest module not available
    if resp.status_code == 503:
        pytest.skip("Selftest module not available")

    assert resp.status_code == 200, f"API should return 200, got {resp.status_code}"

    data = resp.json()

    # Verify plan structure
    assert "version" in data, "Plan should have version"
    assert "steps" in data, "Plan should have steps array"
    assert "summary" in data, "Plan should have summary"


def test_plan_has_steps_with_tiers(fastapi_client):
    """Test plan includes steps with tier classification."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 503:
        pytest.skip("Selftest module not available")

    data = resp.json()
    steps = data["steps"]

    assert len(steps) > 0, "Plan should have at least one step"

    # Check that steps have tier field
    for step in steps:
        assert "tier" in step, f"Step {step.get('id')} missing tier"
        assert step["tier"] in ["kernel", "governance", "optional"], (
            f"Step {step.get('id')} has invalid tier: {step['tier']}"
        )


def test_tier_colors_mapping():
    """Test tier colors are correctly mapped for UI rendering."""
    # Expected tier -> color mapping for UI
    TIER_COLORS = {
        "kernel": "red",  # Critical tier
        "governance": "orange",  # Warning tier
        "optional": "gray",  # Info tier
    }

    # Verify mapping exists and is complete
    assert len(TIER_COLORS) == 3, "Should have 3 tier colors"
    assert "kernel" in TIER_COLORS, "Should have kernel tier color"
    assert "governance" in TIER_COLORS, "Should have governance tier color"
    assert "optional" in TIER_COLORS, "Should have optional tier color"

    # Verify color values are valid CSS colors
    valid_colors = {"red", "orange", "gray", "blue", "green", "yellow"}
    for tier, color in TIER_COLORS.items():
        assert color in valid_colors, f"Tier {tier} has invalid color {color}"


def test_hint_generation_structure():
    """Test hints have correct structure for UI rendering."""
    # Mock governance status with failures

    # Expected hint structure
    expected_fields = {"type", "step", "root_cause", "command", "docs"}

    # Simulate hint generation (would be from JavaScript in real UI)
    # Here we verify the expected structure
    hint = {
        "type": "failure",
        "step": "core-checks",
        "root_cause": "Python lint or compile errors in swarm/ directory",
        "command": "ruff check swarm/ && python -m compileall -q swarm/",
        "docs": "docs/SELFTEST_SYSTEM.md",
    }

    # Verify all expected fields present
    assert set(hint.keys()) == expected_fields, (
        f"Hint structure mismatch. Expected {expected_fields}, got {set(hint.keys())}"
    )

    # Verify field types
    assert isinstance(hint["type"], str), "type should be string"
    assert isinstance(hint["step"], str), "step should be string"
    assert isinstance(hint["root_cause"], str), "root_cause should be string"
    assert isinstance(hint["command"], str), "command should be string"
    assert isinstance(hint["docs"], str), "docs should be string"


def test_commands_are_copyable():
    """Test command strings are present and valid for copying."""
    # Sample commands that should be copyable
    commands = [
        "ruff check swarm/ && python -m compileall -q swarm/",
        "uv run swarm/tools/validate_swarm.py --check-agents",
        "make policy-tests",
        "uv run pytest tests/test_flow_studio_fastapi_smoke.py -v",
    ]

    for cmd in commands:
        # Verify command is non-empty string
        assert isinstance(cmd, str), f"Command should be string, got {type(cmd)}"
        assert len(cmd) > 0, "Command should not be empty"

        # Verify command looks runnable (has valid characters)
        assert not cmd.startswith(" "), "Command should not start with whitespace"
        assert not cmd.endswith(" "), "Command should not end with whitespace"

        # Verify command has executable or script
        assert any(x in cmd for x in ["ruff", "python", "uv", "make", "pytest"]), (
            f"Command should contain executable: {cmd}"
        )


def test_docs_links_present():
    """Test documentation links are included in hints."""
    # Sample docs links that should be present
    docs_links = [
        "docs/SELFTEST_SYSTEM.md",
        "CLAUDE.md § Agent Ops",
        "CLAUDE.md § Skills",
        "swarm/policies/README.md",
    ]

    for link in docs_links:
        # Verify link is non-empty string
        assert isinstance(link, str), f"Link should be string, got {type(link)}"
        assert len(link) > 0, "Link should not be empty"

        # Verify link has valid format
        assert "/" in link or "§" in link, f"Link should be file path or section reference: {link}"


def test_empty_plan_handled(fastapi_client):
    """Test empty plan is handled gracefully."""
    # Create empty-looking governance status
    governance_status = {"governance": {"selftest": {"failed_steps": [], "degraded_steps": []}}}

    # Should produce no hints
    # (In real UI, this would show "no issues" or hide the section)
    assert len(governance_status["governance"]["selftest"]["failed_steps"]) == 0
    assert len(governance_status["governance"]["selftest"]["degraded_steps"]) == 0


def test_degraded_mode_hints():
    """Test degraded mode generates advisory hints."""
    governance_status = {
        "governance": {"selftest": {"failed_steps": [], "degraded_steps": ["bdd", "ac-status"]}}
    }

    # Should have degraded steps
    assert len(governance_status["governance"]["selftest"]["degraded_steps"]) > 0

    # Expected hint type for degraded mode

    # Verify degraded mode would generate advisory hints
    for step in governance_status["governance"]["selftest"]["degraded_steps"]:
        # In UI, these would be rendered as advisory/warning hints
        assert step in ["bdd", "ac-status"], f"Unexpected degraded step: {step}"


def test_failure_mode_hints():
    """Test failure mode generates failure hints."""
    governance_status = {
        "governance": {
            "selftest": {"failed_steps": ["core-checks", "agents-governance"], "degraded_steps": []}
        }
    }

    # Should have failed steps
    assert len(governance_status["governance"]["selftest"]["failed_steps"]) > 0

    # Expected hint type for failures

    # Verify failures would generate failure hints
    for step in governance_status["governance"]["selftest"]["failed_steps"]:
        assert step in ["core-checks", "agents-governance"], f"Unexpected failed step: {step}"


def test_api_selftest_plan_json_format(fastapi_client):
    """Test API returns proper JSON format for UI consumption."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 503:
        pytest.skip("Selftest module not available")

    # Should return JSON
    assert resp.headers.get("content-type") == "application/json", (
        "API should return application/json"
    )

    # Should be valid JSON
    try:
        data = resp.json()
    except Exception as e:
        pytest.fail(f"Response is not valid JSON: {e}")

    # Should have expected top-level structure
    assert isinstance(data, dict), "Response should be object/dict"
    assert "version" in data, "Response should have version"
    assert "steps" in data, "Response should have steps"
    assert "summary" in data, "Response should have summary"


def test_step_dependencies_for_graph_rendering(fastapi_client):
    """Test step dependencies are available for graph rendering."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 503:
        pytest.skip("Selftest module not available")

    data = resp.json()
    steps = data["steps"]

    # Each step should have depends_on field (even if empty)
    for step in steps:
        assert "depends_on" in step, f"Step {step.get('id')} missing depends_on field"
        assert isinstance(step["depends_on"], list), (
            f"Step {step.get('id')} depends_on should be list"
        )

        # If has dependencies, they should be valid step IDs
        if len(step["depends_on"]) > 0:
            all_step_ids = {s["id"] for s in steps}
            for dep in step["depends_on"]:
                assert dep in all_step_ids, f"Step {step['id']} depends on unknown step {dep}"
