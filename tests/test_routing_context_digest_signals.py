"""
Tests for build_context_digest diff, forensic and loop signals, plus its size
budget and robustness against malformed input.

Core digest shape and verification signals are covered in
tests/test_routing_context_digest.py.
"""

import pytest
from routing_digest_support import parse_digest
from swarm.runtime.stepwise.routing.navigator import build_context_digest


class TestFileChangeSignals:
    """Tests for diff scan reporting."""

    def test_reports_file_and_line_counts(self):
        """File count and insertion/deletion totals are included."""
        fields = parse_digest(
            build_context_digest(
                "s",
                0,
                {},
                file_changes={
                    "files": [1, 2, 3],
                    "total_insertions": 40,
                    "total_deletions": 5,
                },
            )
        )

        assert fields["files"] == "3"
        assert fields["lines"] == "+40/-5"

    def test_reports_empty_diff_distinctly(self):
        """A scan that ran and found nothing reports zero, not silence.

        This is the reward-hacking signal: a step claiming success with an
        empty diff must be visible to the Navigator.
        """
        fields = parse_digest(
            build_context_digest(
                "s", 0, {}, file_changes={"files": [], "total_insertions": 0, "total_deletions": 0}
            )
        )

        assert fields["files"] == "0"
        assert fields["lines"] == "+0/-0"

    def test_reports_untracked_files(self):
        """Untracked files are counted when present."""
        fields = parse_digest(
            build_context_digest("s", 0, {}, file_changes={"files": [], "untracked": ["a", "b"]})
        )

        assert fields["untracked"] == "2"

    def test_reports_scan_error(self):
        """A failed scan is flagged rather than read as a clean tree."""
        fields = parse_digest(
            build_context_digest("s", 0, {}, file_changes={"files": [], "scan_error": "no repo"})
        )

        assert fields["scan"] == "error"


class TestForensicSignals:
    """Tests for claim-vs-evidence reporting."""

    def test_reports_verified_claim(self):
        """A trusted claim is reported as ok."""
        fields = parse_digest(
            build_context_digest("s", 0, {}, forensic_verdict={"claim_verified": True})
        )

        assert fields["claim"] == "ok"

    def test_reports_suspect_claim(self):
        """An unverified claim is reported as suspect."""
        fields = parse_digest(
            build_context_digest("s", 0, {}, forensic_verdict={"claim_verified": False})
        )

        assert fields["claim"] == "suspect"

    def test_reports_confidence_and_recommendation(self):
        """Confidence is formatted to two decimals alongside the verdict."""
        fields = parse_digest(
            build_context_digest(
                "s",
                0,
                {},
                forensic_verdict={
                    "claim_verified": False,
                    "confidence": 0.4237,
                    "recommendation": "DISTRUST",
                },
            )
        )

        assert fields["confidence"] == "0.42"
        assert fields["verdict"] == "DISTRUST"

    def test_reports_reward_hacking_flags(self):
        """Reward-hacking flags are surfaced."""
        digest = build_context_digest(
            "s",
            0,
            {},
            forensic_verdict={"claim_verified": False, "reward_hacking_flags": ["NO_DIFF"]},
        )

        assert "NO_DIFF" in digest

    def test_reports_zero_confidence(self):
        """Zero confidence is reported, not treated as absent."""
        fields = parse_digest(
            build_context_digest("s", 0, {}, forensic_verdict={"confidence": 0.0})
        )

        assert fields["confidence"] == "0.00"


class TestLoopSignals:
    """Tests for microloop reporting."""

    def test_reports_loop_count_for_this_step(self):
        """The loop count for the routed step is included."""
        fields = parse_digest(build_context_digest("build-3", 2, {}, loop_state={"build-3": 2}))

        assert fields["loops"] == "2"

    def test_ignores_loop_counts_for_other_steps(self):
        """Other steps' loop counts are not reported."""
        assert "loops" not in build_context_digest("build-3", 0, {}, loop_state={"plan-1": 5})


class TestBudget:
    """Tests for digest size.

    NavigationOrchestrator truncates context to 500 characters before it
    reaches the prompt, so a realistic digest must fit inside that budget or
    the tail signals are silently dropped.
    """

    def test_realistic_digest_fits_navigator_budget(self):
        """A fully-populated digest stays under the 500 char prompt limit."""
        digest = build_context_digest(
            "build-3-code-implementer",
            4,
            {"status": "UNVERIFIED", "duration_ms": 128000},
            verification_result={
                "passed": False,
                "checks": [
                    {"name": f"check-{i}", "passed": i % 2 == 0, "message": "x" * 40}
                    for i in range(12)
                ],
            },
            file_changes={
                "files": list(range(40)),
                "total_insertions": 1200,
                "total_deletions": 340,
                "untracked": ["a", "b", "c"],
            },
            forensic_verdict={
                "claim_verified": False,
                "confidence": 0.31,
                "recommendation": "DISTRUST",
                "reward_hacking_flags": ["NO_DIFF", "TEST_WEAKENED", "SCOPE_DRIFT", "EXTRA"],
            },
            loop_state={"build-3-code-implementer": 4},
        )

        assert len(digest) < 500, f"digest too long ({len(digest)} chars): {digest}"


class TestRobustness:
    """Tests that the digest never breaks a routing decision."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"verification_result": {}},
            {"file_changes": {}},
            {"forensic_verdict": {}},
            {"loop_state": {}},
            {"verification_result": {"checks": None}},
            {"file_changes": {"files": None, "untracked": None}},
            {"forensic_verdict": {"reward_hacking_flags": None}},
        ],
    )
    def test_tolerates_empty_and_null_signal_containers(self, kwargs):
        """Empty or null containers degrade to omitted clauses, not errors."""
        digest = build_context_digest("s", 0, {}, **kwargs)

        assert digest.startswith("step=s iter=0")
