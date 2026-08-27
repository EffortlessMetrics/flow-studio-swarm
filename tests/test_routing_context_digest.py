"""
Tests for build_context_digest (swarm/runtime/stepwise/routing/navigator.py).

The digest is the compact summary of the signals a routing decision was made
on. It is handed to the Navigator as `context` and persisted next to the
candidate set, so it has to stay compact, stable, and honest about what was
not measured.
"""

import pytest
from swarm.runtime.stepwise.routing.navigator import build_context_digest


def parse_digest(digest: str) -> dict:
    """Split a digest into its key=value clauses.

    Values containing spaces are bracketed (e.g. failed=[a, b]), so split on
    keys rather than on whitespace.
    """
    import re

    return {m.group(1): m.group(2) for m in re.finditer(r"(\w+)=(\[[^\]]*\]|\S+)", digest)}


class TestMinimalDigest:
    """Tests for the always-present core of the digest."""

    def test_includes_step_and_iteration(self):
        """Step id and iteration are always present."""
        fields = parse_digest(build_context_digest("build-3", 2, {}))

        assert fields["step"] == "build-3"
        assert fields["iter"] == "2"

    def test_includes_step_status(self):
        """Step status is carried through when present."""
        fields = parse_digest(build_context_digest("build-3", 0, {"status": "VERIFIED"}))

        assert fields["status"] == "VERIFIED"

    def test_omits_absent_signals(self):
        """Signals that were not measured are omitted, not defaulted.

        An absent clause must mean "not measured" rather than "zero", so a
        caller reading the digest cannot mistake a missing scan for a clean one.
        """
        fields = parse_digest(build_context_digest("build-3", 0, {}))

        assert set(fields) == {"step", "iter"}
        assert "files" not in fields
        assert "verify" not in fields
        assert "claim" not in fields

    def test_omits_zero_duration(self):
        """A zero/absent duration is not reported."""
        assert "duration_ms" not in build_context_digest("s", 0, {"duration_ms": 0})

    def test_is_single_line(self):
        """The digest never spans lines - it is embedded in a prompt."""
        digest = build_context_digest(
            "build-3",
            1,
            {"status": "UNVERIFIED"},
            verification_result={"passed": False, "checks": [{"name": "pytest", "passed": False}]},
            file_changes={"files": [1], "total_insertions": 1, "total_deletions": 0},
            forensic_verdict={"claim_verified": False, "confidence": 0.4},
        )

        assert "\n" not in digest


class TestVerificationSignals:
    """Tests for verification reporting."""

    def test_reports_pass(self):
        """A passing verification is reported as pass."""
        fields = parse_digest(
            build_context_digest("s", 0, {}, verification_result={"passed": True})
        )

        assert fields["verify"] == "pass"

    def test_reports_fail(self):
        """A failing verification is reported as fail."""
        fields = parse_digest(
            build_context_digest("s", 0, {}, verification_result={"passed": False})
        )

        assert fields["verify"] == "fail"

    def test_reports_check_ratio(self):
        """Passed/total check counts are included."""
        fields = parse_digest(
            build_context_digest(
                "s",
                0,
                {},
                verification_result={
                    "passed": False,
                    "checks": [
                        {"name": "pytest", "passed": False},
                        {"name": "ruff", "passed": True},
                        {"name": "mypy", "passed": True},
                    ],
                },
            )
        )

        assert fields["checks"] == "2/3"

    def test_names_failed_checks(self):
        """Failing check names are surfaced - that is what routing acts on."""
        digest = build_context_digest(
            "s",
            0,
            {},
            verification_result={
                "passed": False,
                "checks": [{"name": "pytest", "passed": False}],
            },
        )

        assert "pytest" in digest

    def test_truncates_long_failure_lists(self):
        """More than three failures are truncated with a count."""
        checks = [{"name": f"check-{i}", "passed": False} for i in range(6)]

        digest = build_context_digest(
            "s", 0, {}, verification_result={"passed": False, "checks": checks}
        )

        assert "check-0" in digest
        assert "check-5" not in digest
        assert "+3" in digest

    def test_falls_back_to_message_when_name_missing(self):
        """A check without a name is identified by its message."""
        digest = build_context_digest(
            "s",
            0,
            {},
            verification_result={
                "passed": False,
                "checks": [{"message": "coverage below threshold", "passed": False}],
            },
        )

        assert "coverage below threshold" in digest


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
