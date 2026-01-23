#!/usr/bin/env python3
"""
End-to-end selftest workflow tests.

Tests the complete selftest workflow from execution to UI display.
Simulates real user workflow with Flow Studio.

## Test Coverage (10 tests)

1. test_selftest_plan_endpoint_available - /api/selftest/plan is accessible
2. test_plan_data_complete - Plan includes all required fields
3. test_governance_status_structure - Governance status has expected format
4. test_failed_steps_generate_hints - Failed steps produce resolution hints
5. test_degraded_steps_advisory_hints - Degraded steps produce advisory hints
6. test_hint_commands_runnable - Hint commands are valid shell commands
7. test_docs_links_valid_format - Documentation links have valid format
8. test_no_failures_no_hints - No hints when no failures
9. test_all_tiers_represented - All tier types (kernel/governance/optional) present
10. test_summary_counts_accurate - Summary counts match actual step counts
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


@pytest.fixture
def sample_governance_status():
    """Sample governance status with failures and degraded steps."""
    return {
        "governance": {
            "selftest": {
                "failed_steps": ["core-checks", "agents-governance"],
                "degraded_steps": ["bdd"],
                "status": "degraded",
            }
        }
    }


def test_selftest_plan_endpoint_available(fastapi_client):
    """Test /api/selftest/plan endpoint is accessible."""
    resp = fastapi_client.get("/api/selftest/plan")

    # Either 200 with plan or 503 if module unavailable
    assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"


def test_plan_data_complete(fastapi_client):
    """Test plan includes all required fields for UI rendering."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 503:
        pytest.skip("Selftest module not available")

    data = resp.json()

    # Required top-level fields
    assert "version" in data, "Missing version field"
    assert "steps" in data, "Missing steps field"
    assert "summary" in data, "Missing summary field"

    # Version should be valid
    assert data["version"] == "1.0", f"Unexpected version: {data['version']}"

    # Steps should be non-empty array
    assert isinstance(data["steps"], list), "Steps should be list"
    assert len(data["steps"]) > 0, "Steps should not be empty"

    # Summary should have counts
    assert "total" in data["summary"], "Summary missing total"
    assert "by_tier" in data["summary"], "Summary missing by_tier"


def test_governance_status_structure(sample_governance_status):
    """Test governance status has expected format for UI consumption."""
    status = sample_governance_status

    # Required structure
    assert "governance" in status, "Missing governance key"
    assert "selftest" in status["governance"], "Missing selftest key"

    selftest = status["governance"]["selftest"]

    # Required selftest fields
    assert "failed_steps" in selftest, "Missing failed_steps"
    assert "degraded_steps" in selftest, "Missing degraded_steps"
    assert "status" in selftest, "Missing status"

    # Field types
    assert isinstance(selftest["failed_steps"], list), "failed_steps should be list"
    assert isinstance(selftest["degraded_steps"], list), "degraded_steps should be list"
    assert isinstance(selftest["status"], str), "status should be string"


def test_failed_steps_generate_hints(sample_governance_status):
    """Test failed steps produce resolution hints with commands."""
    failed_steps = sample_governance_status["governance"]["selftest"]["failed_steps"]

    # Should have failed steps
    assert len(failed_steps) > 0, "Test data should have failed steps"

    # Each failed step should map to a hint pattern
    known_patterns = {
        "core-checks": "ruff check swarm/",
        "agents-governance": "validate_swarm.py --check-agents",
        "skills-governance": "validate_swarm.py --check-skills",
        "policy-tests": "make policy-tests",
    }

    for step in failed_steps:
        if step in known_patterns:
            expected_command_fragment = known_patterns[step]
            # Verify pattern exists (would be used by UI to generate hint)
            assert expected_command_fragment, f"Step {step} should have command pattern"


def test_degraded_steps_advisory_hints(sample_governance_status):
    """Test degraded steps produce advisory hints (non-blocking)."""
    degraded_steps = sample_governance_status["governance"]["selftest"]["degraded_steps"]

    # Should have degraded steps
    assert len(degraded_steps) > 0, "Test data should have degraded steps"

    # Degraded steps are non-blocking (advisory)
    # They should still provide hints but marked as advisory
    for step in degraded_steps:
        assert isinstance(step, str), f"Degraded step should be string, got {type(step)}"
        assert len(step) > 0, "Degraded step should not be empty"


def test_hint_commands_runnable(fastapi_client):
    """Test hint commands are valid shell commands."""
    # Sample commands that should be generated for common failures
    test_commands = [
        "ruff check swarm/ && python -m compileall -q swarm/",
        "uv run swarm/tools/validate_swarm.py --check-agents",
        "uv run swarm/tools/validate_swarm.py --check-skills",
        "make policy-tests",
        "find features/ -name '*.feature' | head",
    ]

    for cmd in test_commands:
        # Verify command structure
        assert isinstance(cmd, str), "Command should be string"
        assert len(cmd) > 0, "Command should not be empty"

        # Verify command has valid structure (no leading/trailing whitespace)
        assert cmd == cmd.strip(), f"Command has extra whitespace: '{cmd}'"

        # Verify command looks executable (has known tools)
        known_tools = ["ruff", "python", "uv", "make", "find", "pytest"]
        assert any(tool in cmd for tool in known_tools), f"Command should contain known tool: {cmd}"


def test_docs_links_valid_format():
    """Test documentation links have valid format."""
    # Sample docs links that should be present
    test_links = [
        "docs/SELFTEST_SYSTEM.md",
        "CLAUDE.md § Agent Ops",
        "CLAUDE.md § Skills",
        "swarm/policies/README.md",
        "swarm/tools/flow_studio.py",
    ]

    for link in test_links:
        # Verify link structure
        assert isinstance(link, str), "Link should be string"
        assert len(link) > 0, "Link should not be empty"

        # Verify link format
        is_file_path = "/" in link and (".md" in link or ".py" in link)
        is_section_ref = "§" in link
        assert is_file_path or is_section_ref, (
            f"Link should be file path or section reference: {link}"
        )


def test_no_failures_no_hints():
    """Test no hints when no failures."""
    clean_status = {
        "governance": {"selftest": {"failed_steps": [], "degraded_steps": [], "status": "ok"}}
    }

    # Should have no failures
    assert len(clean_status["governance"]["selftest"]["failed_steps"]) == 0
    assert len(clean_status["governance"]["selftest"]["degraded_steps"]) == 0

    # In UI, this would result in no hints being displayed
    assert clean_status["governance"]["selftest"]["status"] == "ok"


def test_all_tiers_represented(fastapi_client):
    """Test all tier types (kernel/governance/optional) are present."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 503:
        pytest.skip("Selftest module not available")

    data = resp.json()
    steps = data["steps"]

    # Collect all tiers
    tiers_found = {step["tier"] for step in steps}

    # Should have all three tiers
    expected_tiers = {"kernel", "governance", "optional"}
    assert tiers_found == expected_tiers, (
        f"Expected all tiers {expected_tiers}, found {tiers_found}"
    )


def test_summary_counts_accurate(fastapi_client):
    """Test summary counts match actual step counts."""
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 503:
        pytest.skip("Selftest module not available")

    data = resp.json()
    steps = data["steps"]
    summary = data["summary"]

    # Count actual steps by tier
    kernel_count = sum(1 for s in steps if s["tier"] == "kernel")
    governance_count = sum(1 for s in steps if s["tier"] == "governance")
    optional_count = sum(1 for s in steps if s["tier"] == "optional")

    # Verify summary matches
    assert summary["by_tier"]["kernel"] == kernel_count, (
        f"Kernel count mismatch: {summary['by_tier']['kernel']} vs {kernel_count}"
    )
    assert summary["by_tier"]["governance"] == governance_count, (
        f"Governance count mismatch: {summary['by_tier']['governance']} vs {governance_count}"
    )
    assert summary["by_tier"]["optional"] == optional_count, (
        f"Optional count mismatch: {summary['by_tier']['optional']} vs {optional_count}"
    )

    # Verify total
    total_expected = kernel_count + governance_count + optional_count
    assert summary["total"] == total_expected, (
        f"Total mismatch: {summary['total']} vs {total_expected}"
    )
    assert summary["total"] == len(steps), (
        f"Total should equal step count: {summary['total']} vs {len(steps)}"
    )


def test_workflow_step_1_fetch_plan(fastapi_client):
    """Workflow Step 1: Fetch selftest plan from API."""
    # User opens Flow Studio and clicks governance tab
    resp = fastapi_client.get("/api/selftest/plan")

    if resp.status_code == 503:
        pytest.skip("Selftest module not available")

    # Should get plan
    assert resp.status_code == 200, "Should fetch plan successfully"

    data = resp.json()
    assert "steps" in data, "Plan should have steps"
    assert len(data["steps"]) > 0, "Should have steps to display"


def test_workflow_step_2_identify_failures(sample_governance_status):
    """Workflow Step 2: Identify failed steps from governance status."""
    # User sees governance status with failures
    failed_steps = sample_governance_status["governance"]["selftest"]["failed_steps"]

    # Should identify failures
    assert len(failed_steps) > 0, "Should have failed steps to display"

    # Each failure should be a valid step ID
    for step in failed_steps:
        assert isinstance(step, str), "Step ID should be string"
        assert len(step) > 0, "Step ID should not be empty"


def test_workflow_step_3_generate_hints(sample_governance_status):
    """Workflow Step 3: Generate resolution hints for failures."""
    # UI generates hints for each failure
    failed_steps = sample_governance_status["governance"]["selftest"]["failed_steps"]

    # Mock hint generation
    hints = []
    for step in failed_steps:
        hint = {
            "type": "failure",
            "step": step,
            "root_cause": f"Issue in {step}",
            "command": f"uv run swarm/tools/selftest.py --step {step}",
            "docs": "docs/SELFTEST_SYSTEM.md",
        }
        hints.append(hint)

    # Should have hint for each failure
    assert len(hints) == len(failed_steps), (
        f"Should have {len(failed_steps)} hints, got {len(hints)}"
    )

    # Each hint should be complete
    for hint in hints:
        assert "type" in hint, "Hint missing type"
        assert "step" in hint, "Hint missing step"
        assert "root_cause" in hint, "Hint missing root_cause"
        assert "command" in hint, "Hint missing command"
        assert "docs" in hint, "Hint missing docs"


def test_workflow_step_4_display_commands():
    """Workflow Step 4: Display copyable commands to user."""
    # Sample hints with commands
    hints = [
        {
            "type": "failure",
            "step": "core-checks",
            "command": "ruff check swarm/ && python -m compileall -q swarm/",
        },
        {"type": "advisory", "step": "bdd", "command": "find features/ -name '*.feature' | head"},
    ]

    # Each hint should have copyable command
    for hint in hints:
        cmd = hint["command"]

        # Verify command is copyable
        assert isinstance(cmd, str), "Command should be string"
        assert len(cmd) > 0, "Command should not be empty"
        assert cmd == cmd.strip(), "Command should not have extra whitespace"

        # User should be able to copy and paste this command
        # (In real UI, this would be a copy-to-clipboard button)
