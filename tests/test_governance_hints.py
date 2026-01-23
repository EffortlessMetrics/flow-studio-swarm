#!/usr/bin/env python3
"""
Governance hints generation tests.

Tests the hint generation system that provides resolution guidance for
selftest failures in Flow Studio.

## Test Coverage (11 tests)

1. test_generate_hints_returns_array - Returns array of hints
2. test_failed_steps_map_to_patterns - Failed steps map to known patterns
3. test_advisory_hints_for_degraded - Advisory hints for degraded mode
4. test_workaround_hints_for_optional - Workaround hints for optional failures
5. test_hints_include_commands - Each hint includes runnable command
6. test_hints_include_docs_links - Each hint includes docs reference
7. test_unknown_step_gets_fallback - Unknown steps get generic fallback
8. test_hint_types_correct - Hint types are correctly assigned
9. test_no_hints_when_no_failures - No hints generated when no failures
10. test_core_checks_pattern - core-checks maps to ruff/compile commands
11. test_agents_governance_pattern - agents-governance maps to validator
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


# Mock the JavaScript hint patterns in Python for testing
HINT_PATTERNS = {
    "core-checks": {
        "type": "failure",
        "root_cause": "Python lint or compile errors in swarm/ directory",
        "command": "ruff check swarm/ && python -m compileall -q swarm/",
        "docs": "docs/SELFTEST_SYSTEM.md",
    },
    "skills-governance": {
        "type": "failure",
        "root_cause": "Invalid or missing skill YAML frontmatter",
        "command": "uv run swarm/tools/validate_swarm.py --check-skills",
        "docs": "CLAUDE.md § Skills",
    },
    "agents-governance": {
        "type": "failure",
        "root_cause": "Agent bijection, color, or frontmatter validation failed",
        "command": "uv run swarm/tools/validate_swarm.py --check-agents",
        "docs": "CLAUDE.md § Agent Ops",
    },
    "bdd": {
        "type": "advisory",
        "root_cause": "BDD feature files missing or malformed",
        "command": "find features/ -name '*.feature' | head",
        "docs": "docs/SELFTEST_SYSTEM.md",
    },
    "ac-status": {
        "type": "advisory",
        "root_cause": "Acceptance criteria tracking incomplete",
        "command": "uv run swarm/tools/selftest.py --step ac-status",
        "docs": "docs/SELFTEST_SYSTEM.md",
    },
    "policy-tests": {
        "type": "failure",
        "root_cause": "OPA policy validation failed",
        "command": "make policy-tests",
        "docs": "swarm/policies/README.md",
    },
    "flowstudio-smoke": {
        "type": "workaround",
        "root_cause": "Flow Studio smoke tests failed (may be missing deps)",
        "command": "uv run pytest tests/test_flow_studio_fastapi_smoke.py -v",
        "docs": "swarm/tools/flow_studio.py",
    },
}


def generate_resolution_hints_python(governance_status):
    """
    Python implementation of generateResolutionHints JavaScript function.

    This mirrors the JavaScript implementation for testing purposes.
    """
    hints = []

    if not governance_status:
        return hints

    governance = governance_status.get("governance", {})
    selftest = governance.get("selftest", {})

    failed_steps = selftest.get("failed_steps", [])
    degraded_steps = selftest.get("degraded_steps", [])

    # Generate hints for failed steps
    for step in failed_steps:
        pattern = HINT_PATTERNS.get(step)
        if pattern:
            hints.append(
                {
                    "type": "failure",
                    "step": step,
                    "root_cause": pattern["root_cause"],
                    "command": pattern["command"],
                    "docs": pattern["docs"],
                }
            )
        else:
            # Fallback for unknown steps
            hints.append(
                {
                    "type": "failure",
                    "step": step,
                    "root_cause": "Check selftest output for details",
                    "command": f"uv run swarm/tools/selftest.py --step {step}",
                    "docs": "docs/SELFTEST_SYSTEM.md",
                }
            )

    # Generate hints for degraded steps (advisory)
    for step in degraded_steps:
        pattern = HINT_PATTERNS.get(step)
        if pattern:
            hints.append(
                {
                    "type": "advisory",
                    "step": step,
                    "root_cause": pattern["root_cause"] + " (non-blocking in degraded mode)",
                    "command": pattern["command"],
                    "docs": pattern["docs"],
                }
            )

    return hints


def test_generate_hints_returns_array():
    """Test generateResolutionHints returns array of hints."""
    governance_status = {
        "governance": {"selftest": {"failed_steps": ["core-checks"], "degraded_steps": []}}
    }

    hints = generate_resolution_hints_python(governance_status)

    assert isinstance(hints, list), "Hints should be a list"
    assert len(hints) > 0, "Should have at least one hint for failed step"


def test_failed_steps_map_to_patterns():
    """Test failed steps map to correct root cause patterns."""
    governance_status = {
        "governance": {
            "selftest": {"failed_steps": ["core-checks", "agents-governance"], "degraded_steps": []}
        }
    }

    hints = generate_resolution_hints_python(governance_status)

    assert len(hints) == 2, f"Expected 2 hints, got {len(hints)}"

    # Check core-checks hint
    core_hint = next((h for h in hints if h["step"] == "core-checks"), None)
    assert core_hint is not None, "Should have hint for core-checks"
    assert "Python lint" in core_hint["root_cause"], (
        f"Unexpected root cause: {core_hint['root_cause']}"
    )
    assert "ruff" in core_hint["command"], f"Expected ruff command, got: {core_hint['command']}"

    # Check agents-governance hint
    agents_hint = next((h for h in hints if h["step"] == "agents-governance"), None)
    assert agents_hint is not None, "Should have hint for agents-governance"
    assert "bijection" in agents_hint["root_cause"].lower(), (
        f"Unexpected root cause: {agents_hint['root_cause']}"
    )
    assert "validate_swarm.py" in agents_hint["command"], (
        f"Expected validate_swarm command, got: {agents_hint['command']}"
    )


def test_advisory_hints_for_degraded():
    """Test advisory hints appear when governance fails but kernel passes."""
    governance_status = {
        "governance": {"selftest": {"failed_steps": [], "degraded_steps": ["bdd", "ac-status"]}}
    }

    hints = generate_resolution_hints_python(governance_status)

    assert len(hints) == 2, f"Expected 2 advisory hints, got {len(hints)}"

    for hint in hints:
        assert hint["type"] == "advisory", f"Expected type 'advisory', got '{hint['type']}'"
        assert "non-blocking in degraded mode" in hint["root_cause"], (
            f"Advisory hint should mention degraded mode: {hint['root_cause']}"
        )


def test_workaround_hints_for_optional():
    """Test hints for optional failures (flowstudio-smoke)."""
    governance_status = {
        "governance": {"selftest": {"failed_steps": ["flowstudio-smoke"], "degraded_steps": []}}
    }

    hints = generate_resolution_hints_python(governance_status)

    assert len(hints) == 1, f"Expected 1 hint, got {len(hints)}"

    hint = hints[0]
    # Note: The pattern type is "workaround", but when in failed_steps
    # the hint generation uses "failure" type. This is expected behavior.
    assert hint["type"] == "failure", (
        f"Expected type 'failure' (from failed_steps), got '{hint['type']}'"
    )
    assert "Flow Studio" in hint["root_cause"], f"Unexpected root cause: {hint['root_cause']}"


def test_hints_include_commands():
    """Test each hint includes runnable command."""
    governance_status = {
        "governance": {
            "selftest": {"failed_steps": ["core-checks", "policy-tests"], "degraded_steps": []}
        }
    }

    hints = generate_resolution_hints_python(governance_status)

    for hint in hints:
        assert "command" in hint, f"Hint missing 'command': {hint}"
        assert isinstance(hint["command"], str), (
            f"Command should be string, got {type(hint['command'])}"
        )
        assert len(hint["command"]) > 0, "Command should not be empty"


def test_hints_include_docs_links():
    """Test each hint includes docs reference."""
    governance_status = {
        "governance": {
            "selftest": {
                "failed_steps": ["skills-governance", "agents-governance"],
                "degraded_steps": [],
            }
        }
    }

    hints = generate_resolution_hints_python(governance_status)

    for hint in hints:
        assert "docs" in hint, f"Hint missing 'docs': {hint}"
        assert isinstance(hint["docs"], str), f"Docs should be string, got {type(hint['docs'])}"
        assert len(hint["docs"]) > 0, "Docs reference should not be empty"

        # Check docs path format
        assert (
            "CLAUDE.md" in hint["docs"]
            or "SELFTEST_SYSTEM.md" in hint["docs"]
            or "README.md" in hint["docs"]
        ), f"Unexpected docs reference: {hint['docs']}"


def test_unknown_step_gets_fallback():
    """Test unknown steps get generic fallback hint."""
    governance_status = {
        "governance": {"selftest": {"failed_steps": ["unknown-step-xyz"], "degraded_steps": []}}
    }

    hints = generate_resolution_hints_python(governance_status)

    assert len(hints) == 1, f"Expected 1 fallback hint, got {len(hints)}"

    hint = hints[0]
    assert hint["step"] == "unknown-step-xyz", (
        f"Expected step 'unknown-step-xyz', got '{hint['step']}'"
    )
    assert "Check selftest output for details" in hint["root_cause"], (
        f"Expected fallback root cause, got: {hint['root_cause']}"
    )
    assert "selftest.py --step unknown-step-xyz" in hint["command"], (
        f"Expected step-specific command, got: {hint['command']}"
    )
    assert hint["docs"] == "docs/SELFTEST_SYSTEM.md", (
        f"Expected SELFTEST_SYSTEM.md, got: {hint['docs']}"
    )


def test_hint_types_correct():
    """Test hint types are correctly assigned based on failed vs degraded."""
    governance_status = {
        "governance": {
            "selftest": {
                "failed_steps": ["core-checks", "flowstudio-smoke"],
                "degraded_steps": ["bdd"],
            }
        }
    }

    hints = generate_resolution_hints_python(governance_status)

    # core-checks should be failure
    core_hint = next((h for h in hints if h["step"] == "core-checks"), None)
    assert core_hint["type"] == "failure", f"core-checks should be failure, got {core_hint['type']}"

    # flowstudio-smoke in failed_steps should be failure
    # (pattern type is "workaround", but failed_steps override to "failure")
    flow_hint = next((h for h in hints if h["step"] == "flowstudio-smoke"), None)
    assert flow_hint["type"] == "failure", (
        f"flowstudio-smoke (in failed_steps) should be failure, got {flow_hint['type']}"
    )

    # bdd (degraded) should be advisory
    bdd_hint = next((h for h in hints if h["step"] == "bdd"), None)
    assert bdd_hint["type"] == "advisory", (
        f"bdd (degraded) should be advisory, got {bdd_hint['type']}"
    )


def test_no_hints_when_no_failures():
    """Test no hints generated when there are no failures."""
    governance_status = {"governance": {"selftest": {"failed_steps": [], "degraded_steps": []}}}

    hints = generate_resolution_hints_python(governance_status)

    assert len(hints) == 0, f"Expected 0 hints for no failures, got {len(hints)}"


def test_core_checks_pattern():
    """Test core-checks maps to ruff/compile commands."""
    pattern = HINT_PATTERNS["core-checks"]

    assert pattern["type"] == "failure", f"core-checks should be failure, got {pattern['type']}"
    assert "ruff check swarm/" in pattern["command"], (
        f"Expected ruff check command: {pattern['command']}"
    )
    assert "python -m compileall" in pattern["command"], (
        f"Expected compileall command: {pattern['command']}"
    )
    assert pattern["docs"] == "docs/SELFTEST_SYSTEM.md", (
        f"Unexpected docs reference: {pattern['docs']}"
    )


def test_agents_governance_pattern():
    """Test agents-governance maps to validator."""
    pattern = HINT_PATTERNS["agents-governance"]

    assert pattern["type"] == "failure", (
        f"agents-governance should be failure, got {pattern['type']}"
    )
    assert "validate_swarm.py --check-agents" in pattern["command"], (
        f"Expected validate_swarm command: {pattern['command']}"
    )
    assert pattern["docs"] == "CLAUDE.md § Agent Ops", (
        f"Unexpected docs reference: {pattern['docs']}"
    )


def test_empty_governance_status():
    """Test handles empty or None governance status gracefully."""
    # Test None
    hints = generate_resolution_hints_python(None)
    assert hints == [], "Should return empty list for None status"

    # Test empty dict
    hints = generate_resolution_hints_python({})
    assert hints == [], "Should return empty list for empty status"

    # Test missing selftest
    hints = generate_resolution_hints_python({"governance": {}})
    assert hints == [], "Should return empty list when selftest missing"
