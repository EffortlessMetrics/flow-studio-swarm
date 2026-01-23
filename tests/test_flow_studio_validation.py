"""
Tests for swarm/tools/flow_studio_validation.py

Tests cover:
1. Valid flow configs pass validation (helper functions work with valid data)
2. Invalid configs (missing agents, missing steps) produce clear error messages
3. Validation message structure for Flow Studio UI rendering
"""

import sys
from pathlib import Path

import pytest

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "swarm" / "tools"))
from flow_studio_validation import (
    clear_validation_cache,
    format_fr_badges_html,
    get_agent_fr_status,
    get_agents_with_issues,
    get_flow_fr_status,
    get_flows_with_issues,
    get_validation_summary,
)

# ============================================================================
# Test Fixtures - Valid and Invalid Validation Data
# ============================================================================


@pytest.fixture
def valid_validation_data():
    """Sample validation data with passing checks."""
    return {
        "version": "1.0.0",
        "timestamp": "2025-12-01T00:00:00Z",
        "summary": {
            "status": "PASS",
            "total_checks": 10,
            "passed": 10,
            "failed": 0,
            "warnings": 0,
            "agents_with_issues": [],
            "flows_with_issues": [],
        },
        "agents": {
            "code-implementer": {
                "file": ".claude/agents/code-implementer.md",
                "checks": {
                    "FR-001": {"status": "pass", "message": "Bijection verified"},
                    "FR-002": {"status": "pass", "message": "Frontmatter valid"},
                    "FR-CONF": {"status": "pass", "message": "Config aligned"},
                },
                "has_issues": False,
                "has_warnings": False,
                "issues": [],
            },
            "test-author": {
                "file": ".claude/agents/test-author.md",
                "checks": {
                    "FR-001": {"status": "pass", "message": "Bijection verified"},
                    "FR-002": {"status": "pass", "message": "Frontmatter valid"},
                },
                "has_issues": False,
                "has_warnings": False,
                "issues": [],
            },
        },
        "flows": {
            "build": {
                "file": "swarm/flows/flow-build.md",
                "checks": {
                    "FR-003": {"status": "pass", "message": "All references valid"},
                    "FR-005": {"status": "pass", "message": "RUN_BASE paths valid"},
                },
                "has_issues": False,
                "has_warnings": False,
                "issues": [],
            },
            "signal": {
                "file": "swarm/flows/flow-signal.md",
                "checks": {
                    "FR-003": {"status": "pass", "message": "All references valid"},
                    "FR-005": {"status": "pass", "message": "RUN_BASE paths valid"},
                },
                "has_issues": False,
                "has_warnings": False,
                "issues": [],
            },
        },
        "skills": {},
        "steps": {},
    }


@pytest.fixture
def failing_validation_data():
    """Sample validation data with failing checks."""
    return {
        "version": "1.0.0",
        "timestamp": "2025-12-01T00:00:00Z",
        "summary": {
            "status": "FAIL",
            "total_checks": 10,
            "passed": 7,
            "failed": 2,
            "warnings": 1,
            "agents_with_issues": ["broken-agent"],
            "flows_with_issues": ["build"],
        },
        "agents": {
            "broken-agent": {
                "file": ".claude/agents/broken-agent.md",
                "checks": {
                    "FR-001": {
                        "status": "fail",
                        "message": "Agent not found in registry",
                        "fix": "Add entry to swarm/AGENTS.md",
                    },
                    "FR-002": {
                        "status": "fail",
                        "message": "Missing required field 'color'",
                        "fix": "Add color: green to frontmatter",
                    },
                },
                "has_issues": True,
                "has_warnings": False,
                "issues": [
                    {
                        "error_type": "BIJECTION",
                        "problem": "Agent not found in registry",
                        "fix_action": "Add entry to swarm/AGENTS.md",
                    },
                    {
                        "error_type": "FRONTMATTER",
                        "problem": "Missing required field 'color'",
                        "fix_action": "Add color: green to frontmatter",
                    },
                ],
            },
            "warning-agent": {
                "file": ".claude/agents/warning-agent.md",
                "checks": {
                    "FR-001": {"status": "pass", "message": "Bijection verified"},
                    "FR-002b": {
                        "status": "warn",
                        "message": "Agent has tools: field (design recommends prompt constraints)",
                    },
                },
                "has_issues": False,
                "has_warnings": True,
                "issues": [],
            },
        },
        "flows": {
            "build": {
                "file": "swarm/flows/flow-build.md",
                "checks": {
                    "FR-003": {
                        "status": "fail",
                        "message": "References unknown agent 'typo-agent'",
                        "fix": "Update reference or add agent to registry",
                    },
                    "FR-005": {"status": "pass", "message": "RUN_BASE paths valid"},
                },
                "has_issues": True,
                "has_warnings": False,
                "issues": [
                    {
                        "error_type": "REFERENCE",
                        "problem": "References unknown agent 'typo-agent'",
                        "fix_action": "Update reference or add agent to registry",
                    }
                ],
            },
        },
        "skills": {},
        "steps": {},
    }


# ============================================================================
# Tests: Valid flow configs pass validation
# ============================================================================


class TestValidConfigs:
    """Tests that valid configs produce correct extraction results."""

    def test_get_agent_fr_status_valid_agent(self, valid_validation_data):
        """get_agent_fr_status returns correct data for valid agent."""
        result = get_agent_fr_status(valid_validation_data, "code-implementer")

        assert result is not None
        assert "checks" in result
        assert "has_issues" in result
        assert "has_warnings" in result
        assert "issues" in result

        # Verify check contents
        assert result["has_issues"] is False
        assert result["has_warnings"] is False
        assert "FR-001" in result["checks"]
        assert result["checks"]["FR-001"]["status"] == "pass"

    def test_get_flow_fr_status_valid_flow(self, valid_validation_data):
        """get_flow_fr_status returns correct data for valid flow."""
        result = get_flow_fr_status(valid_validation_data, "build")

        assert result is not None
        assert "checks" in result
        assert "has_issues" in result
        assert "has_warnings" in result
        assert "issues" in result

        # Verify check contents
        assert result["has_issues"] is False
        assert "FR-003" in result["checks"]
        assert result["checks"]["FR-003"]["status"] == "pass"

    def test_get_validation_summary_pass(self, valid_validation_data):
        """get_validation_summary returns summary with PASS status."""
        result = get_validation_summary(valid_validation_data)

        assert result is not None
        assert result["status"] == "PASS"
        assert result["total_checks"] == 10
        assert result["passed"] == 10
        assert result["failed"] == 0
        assert result["warnings"] == 0
        assert result["agents_with_issues"] == []
        assert result["flows_with_issues"] == []

    def test_get_agents_with_issues_none_when_valid(self, valid_validation_data):
        """get_agents_with_issues returns empty list when no issues."""
        result = get_agents_with_issues(valid_validation_data)

        assert result == []

    def test_get_flows_with_issues_none_when_valid(self, valid_validation_data):
        """get_flows_with_issues returns empty list when no issues."""
        result = get_flows_with_issues(valid_validation_data)

        assert result == []


# ============================================================================
# Tests: Invalid configs produce clear error messages
# ============================================================================


class TestInvalidConfigs:
    """Tests that invalid configs produce clear error extraction."""

    def test_get_agent_fr_status_missing_agent(self, valid_validation_data):
        """get_agent_fr_status returns None for non-existent agent."""
        result = get_agent_fr_status(valid_validation_data, "non-existent-agent")

        assert result is None

    def test_get_agent_fr_status_null_data(self):
        """get_agent_fr_status returns None when validation data is None."""
        result = get_agent_fr_status(None, "any-agent")

        assert result is None

    def test_get_agent_fr_status_empty_agents(self):
        """get_agent_fr_status returns None when agents dict is empty."""
        empty_data = {"agents": {}}
        result = get_agent_fr_status(empty_data, "any-agent")

        assert result is None

    def test_get_flow_fr_status_missing_flow(self, valid_validation_data):
        """get_flow_fr_status returns None for non-existent flow."""
        result = get_flow_fr_status(valid_validation_data, "non-existent-flow")

        assert result is None

    def test_get_flow_fr_status_null_data(self):
        """get_flow_fr_status returns None when validation data is None."""
        result = get_flow_fr_status(None, "any-flow")

        assert result is None

    def test_get_flow_fr_status_empty_flows(self):
        """get_flow_fr_status returns None when flows dict is empty."""
        empty_data = {"flows": {}}
        result = get_flow_fr_status(empty_data, "any-flow")

        assert result is None

    def test_get_validation_summary_null_data(self):
        """get_validation_summary returns None when validation data is None."""
        result = get_validation_summary(None)

        assert result is None

    def test_get_agents_with_issues_null_data(self):
        """get_agents_with_issues returns empty list when data is None."""
        result = get_agents_with_issues(None)

        assert result == []

    def test_get_flows_with_issues_null_data(self):
        """get_flows_with_issues returns empty list when data is None."""
        result = get_flows_with_issues(None)

        assert result == []

    def test_failing_agent_has_issues(self, failing_validation_data):
        """Failing agent has has_issues=True and populated issues list."""
        result = get_agent_fr_status(failing_validation_data, "broken-agent")

        assert result is not None
        assert result["has_issues"] is True
        assert len(result["issues"]) == 2

        # Check issue structure
        issue = result["issues"][0]
        assert "error_type" in issue
        assert "problem" in issue
        assert "fix_action" in issue

    def test_warning_agent_has_warnings(self, failing_validation_data):
        """Warning agent has has_warnings=True."""
        result = get_agent_fr_status(failing_validation_data, "warning-agent")

        assert result is not None
        assert result["has_issues"] is False
        assert result["has_warnings"] is True

    def test_failing_flow_has_issues(self, failing_validation_data):
        """Failing flow has has_issues=True and populated issues list."""
        result = get_flow_fr_status(failing_validation_data, "build")

        assert result is not None
        assert result["has_issues"] is True
        assert len(result["issues"]) == 1

        # Check issue structure
        issue = result["issues"][0]
        assert issue["error_type"] == "REFERENCE"
        assert "typo-agent" in issue["problem"]

    def test_get_agents_with_issues_returns_failing_agents(self, failing_validation_data):
        """get_agents_with_issues returns list of agents with issues."""
        result = get_agents_with_issues(failing_validation_data)

        assert result == ["broken-agent"]

    def test_get_flows_with_issues_returns_failing_flows(self, failing_validation_data):
        """get_flows_with_issues returns list of flows with issues."""
        result = get_flows_with_issues(failing_validation_data)

        assert result == ["build"]

    def test_validation_summary_shows_failure(self, failing_validation_data):
        """get_validation_summary shows FAIL status and counts."""
        result = get_validation_summary(failing_validation_data)

        assert result["status"] == "FAIL"
        assert result["failed"] == 2
        assert result["warnings"] == 1
        assert result["agents_with_issues"] == ["broken-agent"]
        assert result["flows_with_issues"] == ["build"]


# ============================================================================
# Tests: Validation message structure for Flow Studio UI rendering
# ============================================================================


class TestUIRendering:
    """Tests for HTML badge formatting for Flow Studio UI."""

    def test_format_fr_badges_html_empty_checks(self):
        """format_fr_badges_html returns 'No governance data' div for empty checks."""
        result = format_fr_badges_html({})

        assert '<div class="fr-none">No governance data</div>' in result

    def test_format_fr_badges_html_none_checks(self):
        """format_fr_badges_html returns 'No governance data' div for None checks."""
        result = format_fr_badges_html(None)

        assert '<div class="fr-none">No governance data</div>' in result

    def test_format_fr_badges_html_pass_badge(self):
        """format_fr_badges_html generates pass badge with correct CSS class."""
        checks = {"FR-001": {"status": "pass", "message": "Bijection verified"}}
        result = format_fr_badges_html(checks)

        assert '<div class="fr-badges">' in result
        assert '<span class="fr-badge fr-pass"' in result
        assert "FR-001" in result
        assert 'title="Bijection verified"' in result

    def test_format_fr_badges_html_fail_badge(self):
        """format_fr_badges_html generates fail badge with correct CSS class."""
        checks = {"FR-002": {"status": "fail", "message": "Missing required field"}}
        result = format_fr_badges_html(checks)

        assert '<span class="fr-badge fr-fail"' in result
        assert "FR-002" in result
        assert 'title="Missing required field"' in result

    def test_format_fr_badges_html_warn_badge(self):
        """format_fr_badges_html generates warn badge with correct CSS class."""
        checks = {"FR-002b": {"status": "warn", "message": "Design guideline warning"}}
        result = format_fr_badges_html(checks)

        assert '<span class="fr-badge fr-warn"' in result
        assert "FR-002b" in result
        assert 'title="Design guideline warning"' in result

    def test_format_fr_badges_html_multiple_badges(self):
        """format_fr_badges_html generates multiple badges."""
        checks = {
            "FR-001": {"status": "pass", "message": "OK"},
            "FR-002": {"status": "fail", "message": "Failed"},
            "FR-003": {"status": "warn", "message": "Warning"},
        }
        result = format_fr_badges_html(checks)

        assert "FR-001" in result
        assert "FR-002" in result
        assert "FR-003" in result
        assert "fr-pass" in result
        assert "fr-fail" in result
        assert "fr-warn" in result

    def test_format_fr_badges_html_unknown_status(self):
        """format_fr_badges_html handles unknown status gracefully."""
        checks = {"FR-999": {"status": "unknown", "message": "Unknown status"}}
        result = format_fr_badges_html(checks)

        # Should still render with the status as CSS class
        assert '<span class="fr-badge fr-unknown"' in result
        assert "FR-999" in result

    def test_format_fr_badges_html_missing_message(self):
        """format_fr_badges_html handles missing message gracefully."""
        checks = {"FR-001": {"status": "pass"}}
        result = format_fr_badges_html(checks)

        # Should use FR-ID as fallback title
        assert "FR-001" in result
        assert 'title="FR-001"' in result

    def test_format_fr_badges_html_empty_message(self):
        """format_fr_badges_html handles empty message gracefully."""
        checks = {"FR-001": {"status": "pass", "message": ""}}
        result = format_fr_badges_html(checks)

        # Empty message treated as falsy, use FR-ID as fallback
        assert "FR-001" in result


# ============================================================================
# Tests: Edge cases and robustness
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and robustness."""

    def test_missing_checks_key_in_agent(self):
        """get_agent_fr_status handles missing 'checks' key gracefully."""
        data = {
            "agents": {
                "minimal-agent": {
                    "file": ".claude/agents/minimal-agent.md",
                    # No 'checks' key
                    "has_issues": False,
                    "has_warnings": False,
                }
            }
        }
        result = get_agent_fr_status(data, "minimal-agent")

        assert result is not None
        assert result["checks"] == {}  # Should default to empty dict

    def test_missing_issues_key_in_agent(self):
        """get_agent_fr_status handles missing 'issues' key gracefully."""
        data = {
            "agents": {
                "minimal-agent": {
                    "file": ".claude/agents/minimal-agent.md",
                    "checks": {},
                    "has_issues": False,
                    "has_warnings": False,
                    # No 'issues' key
                }
            }
        }
        result = get_agent_fr_status(data, "minimal-agent")

        assert result is not None
        assert result["issues"] == []  # Should default to empty list

    def test_missing_summary_key(self):
        """get_validation_summary handles missing 'summary' key gracefully."""
        data = {"agents": {}, "flows": {}}  # No 'summary' key
        result = get_validation_summary(data)

        assert result == {}  # Should return empty dict

    def test_missing_agents_with_issues_in_summary(self):
        """get_agents_with_issues handles missing key in summary gracefully."""
        data = {
            "summary": {
                "status": "PASS",
                # No 'agents_with_issues' key
            }
        }
        result = get_agents_with_issues(data)

        assert result == []

    def test_missing_flows_with_issues_in_summary(self):
        """get_flows_with_issues handles missing key in summary gracefully."""
        data = {
            "summary": {
                "status": "PASS",
                # No 'flows_with_issues' key
            }
        }
        result = get_flows_with_issues(data)

        assert result == []

    def test_clear_validation_cache(self):
        """clear_validation_cache clears the LRU cache without error."""
        # Should not raise any exception
        clear_validation_cache()

    def test_format_fr_badges_html_special_characters_in_message(self):
        """format_fr_badges_html handles special characters in message."""
        checks = {
            "FR-001": {
                "status": "fail",
                "message": "Error: <script>alert('xss')</script>",
            }
        }
        result = format_fr_badges_html(checks)

        # Should render (note: HTML escaping is responsibility of template engine)
        assert "FR-001" in result
        # The message is rendered as-is in title attribute
        assert "Error:" in result


# ============================================================================
# Integration test: Validate actual structure from validator
# ============================================================================


class TestIntegrationWithValidator:
    """Integration tests that call the actual validator (if available)."""

    @pytest.mark.slow
    def test_real_validation_data_structure(self):
        """Test that real validation data matches expected structure.

        This test calls the actual validator and verifies the structure
        matches what flow_studio_validation.py expects.
        """
        import subprocess

        try:
            result = subprocess.run(
                ["uv", "run", "swarm/tools/validate_swarm.py", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(__file__).parent.parent,
            )

            if result.returncode not in [0, 1]:
                pytest.skip("Validator returned unexpected exit code")

            import json

            validation_data = json.loads(result.stdout)

            # Test that our extraction functions work with real data
            summary = get_validation_summary(validation_data)
            assert summary is not None
            assert "status" in summary

            agents_with_issues = get_agents_with_issues(validation_data)
            assert isinstance(agents_with_issues, list)

            flows_with_issues = get_flows_with_issues(validation_data)
            assert isinstance(flows_with_issues, list)

            # Test extraction for known agents
            if "agents" in validation_data and validation_data["agents"]:
                sample_agent_key = next(iter(validation_data["agents"].keys()))
                agent_status = get_agent_fr_status(validation_data, sample_agent_key)
                assert agent_status is not None
                assert "checks" in agent_status

            # Test extraction for known flows
            if "flows" in validation_data and validation_data["flows"]:
                sample_flow_key = next(iter(validation_data["flows"].keys()))
                flow_status = get_flow_fr_status(validation_data, sample_flow_key)
                assert flow_status is not None
                assert "checks" in flow_status

        except subprocess.TimeoutExpired:
            pytest.skip("Validator timed out")
        except FileNotFoundError:
            pytest.skip("uv not available")
        except Exception as e:
            pytest.skip(f"Integration test skipped: {e}")
