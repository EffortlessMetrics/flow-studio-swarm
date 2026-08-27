"""
Tests for the core shape of build_context_digest and its verification signals.

The digest is the compact summary of the signals a routing decision was made
on. It is handed to the Navigator as `context` and persisted next to the
candidate set, so it has to stay compact, stable, and honest about what was
not measured.

Diff, forensic and loop signals are covered in
tests/test_routing_context_digest_signals.py.
"""

from routing_digest_support import parse_digest
from swarm.runtime.stepwise.routing.navigator import build_context_digest


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
