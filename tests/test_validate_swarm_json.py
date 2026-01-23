"""
Focused tests for validate_swarm.py JSON mode output.

Tests that the --json flag produces valid, stable JSON with correct schema.
"""

import json
import subprocess
from pathlib import Path


def run_validator_json():
    """Run validator with --json flag and return parsed JSON."""
    result = subprocess.run(
        ["uv", "run", "swarm/tools/validate_swarm.py", "--json"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    return json.loads(result.stdout)


def test_validate_swarm_json_valid_schema():
    """Test that --json output has valid, stable schema."""
    data = run_validator_json()

    # Top-level structure
    assert "summary" in data, "Missing 'summary' key"
    assert "agents" in data, "Missing 'agents' key"
    assert "flows" in data, "Missing 'flows' key"
    assert "steps" in data, "Missing 'steps' key"
    assert "skills" in data, "Missing 'skills' key"
    assert "version" in data, "Missing 'version' key"
    assert "timestamp" in data, "Missing 'timestamp' key"

    # Summary structure
    summary = data["summary"]
    assert "status" in summary, "summary missing 'status'"
    assert summary["status"] in ["PASS", "FAIL"], f"Invalid status: {summary['status']}"
    assert "total_checks" in summary, "summary missing 'total_checks'"
    assert "passed" in summary, "summary missing 'passed'"
    assert "failed" in summary, "summary missing 'failed'"
    assert "warnings" in summary, "summary missing 'warnings'"
    assert "agents_with_issues" in summary, "summary missing 'agents_with_issues'"
    assert "flows_with_issues" in summary, "summary missing 'flows_with_issues'"
    assert "steps_with_issues" in summary, "summary missing 'steps_with_issues'"
    assert isinstance(summary["total_checks"], int), "total_checks not an int"
    assert isinstance(summary["passed"], int), "passed not an int"
    assert isinstance(summary["failed"], int), "failed not an int"
    assert isinstance(summary["warnings"], int), "warnings not an int"
    assert isinstance(summary["agents_with_issues"], list), "agents_with_issues not a list"
    assert isinstance(summary["flows_with_issues"], list), "flows_with_issues not a list"

    # Agents structure (if any agents present)
    agents = data["agents"]
    assert isinstance(agents, dict), "agents is not a dict"
    for agent_key, agent_data in agents.items():
        assert "file" in agent_data, f"{agent_key} missing 'file'"
        assert "checks" in agent_data, f"{agent_key} missing 'checks'"
        assert "has_issues" in agent_data, f"{agent_key} missing 'has_issues'"
        assert "has_warnings" in agent_data, f"{agent_key} missing 'has_warnings'"
        assert isinstance(agent_data["has_issues"], bool), f"{agent_key} has_issues not bool"
        assert isinstance(agent_data["has_warnings"], bool), f"{agent_key} has_warnings not bool"

        # Each check should have status, message, fix
        checks = agent_data["checks"]
        for check_name, check_data in checks.items():
            assert "status" in check_data, f"{agent_key}.{check_name} missing 'status'"
            assert check_data["status"] in ["pass", "fail", "warn"], (
                f"Invalid check status: {check_data['status']}"
            )

    # Flows structure (if any flows present)
    flows = data["flows"]
    assert isinstance(flows, dict), "flows is not a dict"

    # Steps structure
    flow_steps = data["steps"]
    assert isinstance(flow_steps, dict), "steps is not a dict"

    # Skills structure
    skills = data["skills"]
    assert isinstance(skills, dict), "skills is not a dict"


def test_validate_swarm_json_agents_with_checks():
    """Test that agents have recognizable FR checks."""
    data = run_validator_json()
    agents = data["agents"]

    # For any present agent, verify it has expected FR checks
    if agents:
        # Get first agent as sample
        sample_agent = next(iter(agents.values()))
        checks = sample_agent["checks"]

        # Should have at least one of these FR checks
        expected_frs = {"FR-001", "FR-002", "FR-002b", "FR-CONF"}
        actual_frs = set(checks.keys())
        found_frs = expected_frs & actual_frs
        assert len(found_frs) > 0, f"Agent checks missing expected FRs. Got: {actual_frs}"


def test_validate_swarm_json_flows_with_checks():
    """Test that flows have recognizable FR checks."""
    data = run_validator_json()
    flows = data["flows"]

    # For any present flow, verify it has expected FR checks
    if flows:
        # Get first flow as sample
        sample_flow = next(iter(flows.values()))
        checks = sample_flow["checks"]

        # Should have at least one of these FR checks
        expected_frs = {"FR-003", "FR-005", "FR-FLOWS"}
        actual_frs = set(checks.keys())
        found_frs = expected_frs & actual_frs
        assert len(found_frs) > 0, f"Flow checks missing expected FRs. Got: {actual_frs}"


def test_validate_swarm_json_output_parseable():
    """Test that JSON output is well-formed and parseable."""
    result = subprocess.run(
        ["uv", "run", "swarm/tools/validate_swarm.py", "--json"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    # Should exit with 0 or 1 (0=PASS, 1=FAIL, both are valid)
    assert result.returncode in [0, 1], f"Unexpected exit code: {result.returncode}"

    # Stdout should be valid JSON
    try:
        data = json.loads(result.stdout)
        assert isinstance(data, dict), "JSON root is not a dict"
    except json.JSONDecodeError as e:
        raise AssertionError(f"JSON parse error: {e}")
