"""Tests for history priority classification (v2.5.0).

Tests the HistoryPriority enum, classify_history_item function, and
prioritize_history sorting. These tests ensure that:
1. Critical agents (deciders, critics, implementers) get CRITICAL priority
2. Foundation agents (requirements, design, verification) get HIGH priority
3. Analysis agents (risk, impact, context) get MEDIUM priority
4. Utility agents (reporters, historians, post-flight) get LOW priority
"""

import sys
from pathlib import Path

import pytest

_SWARM_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SWARM_ROOT))

from swarm.runtime.history_priority import (
    CRITICAL_AGENT_PATTERNS,
    HIGH_AGENT_PATTERNS,
    LOW_AGENT_PATTERNS,
    MEDIUM_AGENT_PATTERNS,
    HistoryPriority,
    classify_history_item,
    get_priority_label,
    prioritize_history,
    summarize_priority_distribution,
)


class TestHistoryPriorityEnum:
    """Tests for the HistoryPriority enum."""

    def test_priority_ordering(self):
        """Higher priority values are numerically larger."""
        assert HistoryPriority.CRITICAL > HistoryPriority.HIGH
        assert HistoryPriority.HIGH > HistoryPriority.MEDIUM
        assert HistoryPriority.MEDIUM > HistoryPriority.LOW

    def test_priority_values(self):
        """Priority values match expected integers."""
        assert HistoryPriority.LOW == 0
        assert HistoryPriority.MEDIUM == 1
        assert HistoryPriority.HIGH == 2
        assert HistoryPriority.CRITICAL == 3

    def test_priority_is_comparable(self):
        """Priorities can be compared with integers."""
        assert HistoryPriority.CRITICAL >= 3
        assert HistoryPriority.LOW < 1


class TestClassifyHistoryItem:
    """Tests for classify_history_item function."""

    # CRITICAL agents
    @pytest.mark.parametrize(
        "agent_key",
        [
            "merge-decider",
            "deploy-decider",
            "requirements-critic",
            "design-critic",
            "test-critic",
            "code-critic",
            "code-implementer",
            "test-author",
            "self-reviewer",
        ],
    )
    def test_critical_agents(self, agent_key: str):
        """Critical agents are classified as CRITICAL."""
        item = {"agent_key": agent_key, "step_id": "test", "output": "test output"}
        assert classify_history_item(item) == HistoryPriority.CRITICAL

    # HIGH agents
    @pytest.mark.parametrize(
        "agent_key",
        [
            "requirements-author",
            "bdd-author",
            "adr-author",
            "interface-designer",
            "observability-designer",
            "receipt-checker",
            "contract-enforcer",
            "security-scanner",
            "coverage-enforcer",
            "smoke-verifier",
        ],
    )
    def test_high_agents(self, agent_key: str):
        """Foundation agents are classified as HIGH."""
        item = {"agent_key": agent_key, "step_id": "test", "output": "test output"}
        assert classify_history_item(item) == HistoryPriority.HIGH

    # MEDIUM agents
    @pytest.mark.parametrize(
        "agent_key",
        [
            "clarifier",
            "risk-analyst",
            "policy-analyst",
            "impact-analyzer",
            "context-loader",
            "fixer",
            "mutator",
        ],
    )
    def test_medium_agents(self, agent_key: str):
        """Analysis agents are classified as MEDIUM."""
        item = {"agent_key": agent_key, "step_id": "test", "output": "test output"}
        assert classify_history_item(item) == HistoryPriority.MEDIUM

    # LOW agents
    @pytest.mark.parametrize(
        "agent_key",
        [
            "signal-normalizer",
            "problem-framer",
            "scope-assessor",
            "gh-reporter",
            "doc-writer",
            "flow-historian",
            "artifact-auditor",
            "regression-analyst",
            "learning-synthesizer",
            "feedback-applier",
            "repo-operator",
        ],
    )
    def test_low_agents(self, agent_key: str):
        """Utility agents are classified as LOW."""
        item = {"agent_key": agent_key, "step_id": "test", "output": "test output"}
        assert classify_history_item(item) == HistoryPriority.LOW

    def test_unknown_agent_defaults_to_medium(self):
        """Unknown agents default to MEDIUM (safe middle ground)."""
        # Use step_id that won't match any pattern
        item = {"agent_key": "unknown-agent-xyz", "step_id": "some_random_step", "output": ""}
        assert classify_history_item(item) == HistoryPriority.MEDIUM

    def test_missing_agent_key_uses_step_id(self):
        """When agent_key is missing, step_id patterns are used."""
        item = {"step_id": "critic_review", "output": ""}
        assert classify_history_item(item) == HistoryPriority.CRITICAL

        item = {"step_id": "implement_feature", "output": ""}
        assert classify_history_item(item) == HistoryPriority.HIGH

    def test_agents_list_format(self):
        """Agent key can be in 'agents' list format."""
        item = {"agents": ["code-implementer"], "step_id": "test", "output": ""}
        assert classify_history_item(item) == HistoryPriority.CRITICAL

    def test_artifact_patterns_in_output(self):
        """Output content affects priority for unknown agents."""
        # High-value artifact patterns
        item = {"step_id": "step1", "output": "## Decision: approved"}
        assert classify_history_item(item) == HistoryPriority.HIGH

        # Low-value artifact patterns
        item = {"step_id": "step1", "output": "## Summary of the run"}
        assert classify_history_item(item) == HistoryPriority.LOW


class TestPrioritizeHistory:
    """Tests for prioritize_history function."""

    def test_empty_history(self):
        """Empty history returns empty list."""
        result = prioritize_history([])
        assert result == []

    def test_single_item(self):
        """Single item is returned correctly."""
        history = [{"agent_key": "code-implementer", "step_id": "s1", "output": ""}]
        result = prioritize_history(history)
        assert len(result) == 1
        priority, idx, item = result[0]
        assert priority == HistoryPriority.CRITICAL
        assert idx == 0

    def test_sorting_by_priority(self):
        """Items are sorted by priority descending."""
        history = [
            {"agent_key": "gh-reporter", "step_id": "s1", "output": ""},  # LOW
            {"agent_key": "code-implementer", "step_id": "s2", "output": ""},  # CRITICAL
            {"agent_key": "risk-analyst", "step_id": "s3", "output": ""},  # MEDIUM
            {"agent_key": "adr-author", "step_id": "s4", "output": ""},  # HIGH
        ]
        result = prioritize_history(history)

        # Should be sorted: CRITICAL, HIGH, MEDIUM, LOW
        priorities = [p for p, _, _ in result]
        assert priorities == [
            HistoryPriority.CRITICAL,
            HistoryPriority.HIGH,
            HistoryPriority.MEDIUM,
            HistoryPriority.LOW,
        ]

    def test_preserves_order_within_priority(self):
        """Items with same priority maintain chronological order."""
        history = [
            {"agent_key": "code-implementer", "step_id": "impl1", "output": ""},  # CRITICAL (idx 0)
            {"agent_key": "test-author", "step_id": "test1", "output": ""},  # CRITICAL (idx 1)
            {"agent_key": "code-critic", "step_id": "critic1", "output": ""},  # CRITICAL (idx 2)
        ]
        result = prioritize_history(history, preserve_order_within_priority=True)

        # All CRITICAL, should maintain original order (0, 1, 2)
        indices = [idx for _, idx, _ in result]
        assert indices == [0, 1, 2]

    def test_original_index_preserved(self):
        """Original index is preserved in result tuple."""
        history = [
            {"agent_key": "gh-reporter", "step_id": "s1", "output": ""},  # LOW at idx 0
            {"agent_key": "code-implementer", "step_id": "s2", "output": ""},  # CRITICAL at idx 1
        ]
        result = prioritize_history(history)

        # First result should be CRITICAL with original index 1
        priority, orig_idx, item = result[0]
        assert priority == HistoryPriority.CRITICAL
        assert orig_idx == 1
        assert item["step_id"] == "s2"


class TestGetPriorityLabel:
    """Tests for get_priority_label function."""

    def test_all_labels(self):
        """All priority levels have labels."""
        assert get_priority_label(HistoryPriority.CRITICAL) == "CRITICAL"
        assert get_priority_label(HistoryPriority.HIGH) == "HIGH"
        assert get_priority_label(HistoryPriority.MEDIUM) == "MEDIUM"
        assert get_priority_label(HistoryPriority.LOW) == "LOW"


class TestSummarizePriorityDistribution:
    """Tests for summarize_priority_distribution function."""

    def test_empty_history(self):
        """Empty history returns zero counts."""
        result = summarize_priority_distribution([])
        assert result == {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    def test_mixed_priorities(self):
        """Counts are correct for mixed priorities."""
        history = [
            {"agent_key": "code-implementer", "step_id": "s1", "output": ""},  # CRITICAL
            {"agent_key": "code-critic", "step_id": "s2", "output": ""},  # CRITICAL
            {"agent_key": "adr-author", "step_id": "s3", "output": ""},  # HIGH
            {"agent_key": "risk-analyst", "step_id": "s4", "output": ""},  # MEDIUM
            {"agent_key": "gh-reporter", "step_id": "s5", "output": ""},  # LOW
            {"agent_key": "doc-writer", "step_id": "s6", "output": ""},  # LOW
        ]
        result = summarize_priority_distribution(history)
        assert result == {"CRITICAL": 2, "HIGH": 1, "MEDIUM": 1, "LOW": 2}


class TestAgentPatternSets:
    """Tests for agent pattern sets consistency."""

    def test_no_overlap_between_sets(self):
        """Agent pattern sets don't overlap."""
        all_sets = [
            CRITICAL_AGENT_PATTERNS,
            HIGH_AGENT_PATTERNS,
            MEDIUM_AGENT_PATTERNS,
            LOW_AGENT_PATTERNS,
        ]
        for i, set_a in enumerate(all_sets):
            for j, set_b in enumerate(all_sets):
                if i != j:
                    overlap = set_a & set_b
                    assert overlap == set(), f"Overlap between sets {i} and {j}: {overlap}"

    def test_all_sets_are_frozensets(self):
        """All pattern sets are frozensets (immutable)."""
        assert isinstance(CRITICAL_AGENT_PATTERNS, frozenset)
        assert isinstance(HIGH_AGENT_PATTERNS, frozenset)
        assert isinstance(MEDIUM_AGENT_PATTERNS, frozenset)
        assert isinstance(LOW_AGENT_PATTERNS, frozenset)


class TestAgentTaxonomyCoverage:
    """Tests that all defined agents are covered by the priority classifier.

    This is a safety net to ensure new agents are added to the priority
    mapping and don't silently fall through to MEDIUM default.
    """

    def test_all_config_agents_are_classified(self):
        """Every agent in swarm/config/agents/ should be in a priority tier.

        This test prevents agent taxonomy drift where new agents are added
        but not explicitly classified, causing them to silently default to MEDIUM.
        """
        # Get all agent keys from config files
        config_agents_dir = _SWARM_ROOT / "swarm" / "config" / "agents"
        if not config_agents_dir.exists():
            pytest.skip("swarm/config/agents/ directory not found")

        config_agent_keys = set()
        for yaml_file in config_agents_dir.glob("*.yaml"):
            agent_key = yaml_file.stem  # e.g., "code-critic.yaml" -> "code-critic"
            config_agent_keys.add(agent_key)

        # Get all explicitly classified agents
        classified_agents = (
            CRITICAL_AGENT_PATTERNS
            | HIGH_AGENT_PATTERNS
            | MEDIUM_AGENT_PATTERNS
            | LOW_AGENT_PATTERNS
        )

        # Find agents that are NOT explicitly classified
        unclassified = config_agent_keys - classified_agents

        # This should be empty - all agents should be explicitly classified
        assert unclassified == set(), (
            f"Found {len(unclassified)} agent(s) not explicitly classified in history_priority.py:\n"
            f"  {sorted(unclassified)}\n\n"
            f"These agents will default to MEDIUM priority. If this is intentional, "
            f"add them to MEDIUM_AGENT_PATTERNS. Otherwise, add them to the "
            f"appropriate tier (CRITICAL, HIGH, MEDIUM, or LOW).\n\n"
            f"See docs/CONTEXT_BUDGETS.md 'Priority-Aware History Selection' for guidance."
        )

    def test_no_stale_agent_references(self):
        """Priority patterns should not reference agents that don't exist.

        This catches stale references to agents that were renamed or removed.
        """
        config_agents_dir = _SWARM_ROOT / "swarm" / "config" / "agents"
        if not config_agents_dir.exists():
            pytest.skip("swarm/config/agents/ directory not found")

        config_agent_keys = set()
        for yaml_file in config_agents_dir.glob("*.yaml"):
            agent_key = yaml_file.stem
            config_agent_keys.add(agent_key)

        # Get all explicitly classified agents
        classified_agents = (
            CRITICAL_AGENT_PATTERNS
            | HIGH_AGENT_PATTERNS
            | MEDIUM_AGENT_PATTERNS
            | LOW_AGENT_PATTERNS
        )

        # Find classified agents that don't exist in config
        stale_references = classified_agents - config_agent_keys

        # Allow empty set (no stale references) - this is the ideal state
        # Note: We don't fail on this because the classifier might intentionally
        # include patterns that aren't agent keys (for future expansion)
        if stale_references:
            # Just warn, don't fail - patterns can be intentionally broader
            import warnings

            warnings.warn(
                f"Priority patterns include {len(stale_references)} key(s) not in config/agents/: "
                f"{sorted(stale_references)}. This may be intentional for future agents.",
                UserWarning,
            )

    def test_critical_agents_complete(self):
        """All 10 CRITICAL agents should be present."""
        expected_critical = {
            "merge-decider",
            "deploy-decider",
            "requirements-critic",
            "design-critic",
            "test-critic",
            "code-critic",
            "ux-critic",
            "code-implementer",
            "test-author",
            "self-reviewer",
        }
        assert CRITICAL_AGENT_PATTERNS == expected_critical, (
            f"CRITICAL agents mismatch:\n"
            f"  Missing: {expected_critical - CRITICAL_AGENT_PATTERNS}\n"
            f"  Extra: {CRITICAL_AGENT_PATTERNS - expected_critical}"
        )
