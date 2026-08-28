"""
Tests for routing context digest bounds and robustness.

The digest is a diagnostic sent to a cheap LLM call: it must stay within a
token budget and must never break routing on partial or malformed context.
Rendering behavior lives in test_routing_context_digest.py.
"""

import pytest
from swarm.runtime.stepwise.routing.context_digest import (
    MAX_DIGEST_CHARS,
    build_context_digest,
)


def parse(digest: str) -> dict:
    """Parse a digest string into a key -> value mapping."""
    out = {}
    for part in digest.split("; "):
        if "=" in part:
            key, _, value = part.partition("=")
            out[key] = value
    return out


class TestBounds:
    """The digest is bounded so it cannot crowd out the Navigator prompt."""

    def test_total_length_is_capped(self):
        digest = build_context_digest(
            "build",
            "3",
            1,
            verification_result={"passed": False, "failure_summary": "x" * 5000},
            forensic_verdict={
                "recommendation": "DISTRUST",
                "confidence": 0.1,
                "reward_hacking_flags": ["flag" * 200],
            },
            loop_state={f"step{i}": i + 1 for i in range(50)},
            candidate_count=9,
        )

        assert len(digest) <= MAX_DIGEST_CHARS

    def test_single_field_cannot_consume_the_whole_budget(self):
        """One long failure summary must not squeeze out later signals."""
        digest = build_context_digest(
            "build",
            "3",
            1,
            verification_result={"passed": False, "failure_summary": "y" * 5000},
            candidate_count=4,
        )

        assert "candidates=4" in digest

    def test_multiline_values_are_flattened(self):
        digest = build_context_digest(
            "build",
            "3",
            0,
            verification_result={"passed": False, "failure_summary": "line one\nline two"},
        )

        assert "\n" not in digest
        assert parse(digest)["failure"] == "line one line two"


class TestRobustness:
    """The digest is diagnostic; building it must never break routing."""

    @pytest.mark.parametrize(
        "file_changes",
        [{}, {"unrelated": "value"}, "not-a-mapping", 0],
    )
    def test_unusable_file_changes_are_skipped(self, file_changes):
        digest = build_context_digest("build", "3", 0, file_changes=file_changes)

        assert digest.startswith("flow=build; step=3; iter=0")
        assert "files=" not in digest

    def test_hostile_context_still_produces_position(self):
        class Exploding:
            def __getattr__(self, name):
                raise RuntimeError("boom")

        digest = build_context_digest("build", "3", 1, step_result=Exploding())

        assert digest.startswith("flow=build; step=3; iter=1")

    def test_is_deterministic(self):
        kwargs = dict(
            flow_key="build",
            step_id="3",
            iteration=2,
            step_result={"status": "UNVERIFIED"},
            verification_result={"passed": False, "failure_summary": "boom"},
            file_changes={"files_added": 1},
            loop_state={"3": 2, "1": 1},
            candidate_count=3,
        )

        assert build_context_digest(**kwargs) == build_context_digest(**kwargs)
