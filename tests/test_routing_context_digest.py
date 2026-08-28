"""
Tests for routing context digest rendering.

The digest compresses the forensics behind a routing decision into a short
string sent to the Navigator and recorded in the routing audit trail. This
module covers what the digest says; bounds and failure tolerance live in
test_routing_context_digest_bounds.py.
"""

from types import SimpleNamespace

from swarm.runtime.stepwise.routing.context_digest import build_context_digest


def parse(digest: str) -> dict:
    """Parse a digest string into a key -> value mapping."""
    out = {}
    for part in digest.split("; "):
        if "=" in part:
            key, _, value = part.partition("=")
            out[key] = value
    return out


class TestPositionFields:
    """The digest always identifies where in the graph the decision happened."""

    def test_minimal_context_yields_position_only(self):
        digest = build_context_digest(flow_key="build", step_id="3", iteration=2)

        assert digest == "flow=build; step=3; iter=2"

    def test_position_present_even_with_rich_context(self):
        digest = build_context_digest(
            flow_key="gate",
            step_id="1",
            iteration=0,
            step_result={"status": "VERIFIED"},
        )
        fields = parse(digest)

        assert fields["flow"] == "gate"
        assert fields["step"] == "1"
        assert fields["iter"] == "0"


class TestOmitsUnmeasuredSignals:
    """Absent signals are omitted, never rendered as false or empty.

    "Not measured" and "measured false" must not look alike in the audit trail.
    """

    def test_no_verify_key_when_verification_absent(self):
        digest = build_context_digest("build", "3", 0, verification_result=None)

        assert "verify=" not in digest

    def test_no_verify_key_when_passed_is_missing(self):
        digest = build_context_digest("build", "3", 0, verification_result={})

        assert "verify=" not in digest

    def test_verify_fail_is_distinct_from_absent(self):
        digest = build_context_digest("build", "3", 0, verification_result={"passed": False})

        assert parse(digest)["verify"] == "fail"

    def test_no_files_key_when_no_changes_reported(self):
        digest = build_context_digest("build", "3", 0, file_changes=None)

        assert "files=" not in digest

    def test_no_forensic_key_without_verdict(self):
        digest = build_context_digest("build", "3", 0, forensic_verdict=None)

        assert "forensic=" not in digest

    def test_zero_iteration_loops_are_omitted(self):
        digest = build_context_digest("build", "3", 0, loop_state={"3": 0, "4": 0})

        assert "loops=" not in digest


class TestSignalRendering:
    """Each signal renders in a compact, parseable form."""

    def test_verification_failure_includes_summary(self):
        digest = build_context_digest(
            "build",
            "3",
            1,
            verification_result={"passed": False, "failure_summary": "2 tests failed"},
        )
        fields = parse(digest)

        assert fields["verify"] == "fail"
        assert fields["failure"] == "2 tests failed"

    def test_passing_verification_omits_failure_detail(self):
        digest = build_context_digest(
            "build",
            "3",
            1,
            verification_result={"passed": True, "failure_summary": "stale"},
        )

        assert parse(digest)["verify"] == "pass"
        assert "failure=" not in digest

    def test_file_changes_from_counts(self):
        digest = build_context_digest(
            "build",
            "3",
            0,
            file_changes={"files_added": 1, "files_modified": 3, "files_deleted": 2},
        )

        assert parse(digest)["files"] == "+1~3-2"

    def test_file_changes_from_lists(self):
        digest = build_context_digest(
            "build",
            "3",
            0,
            file_changes={"added": ["a.py"], "modified": ["b.py", "c.py"], "deleted": []},
        )

        assert parse(digest)["files"] == "+1~2-0"

    def test_file_changes_falls_back_to_total(self):
        digest = build_context_digest("build", "3", 0, file_changes={"total_files": 7})

        assert parse(digest)["files"] == "7"

    def test_forensic_verdict_includes_confidence_and_flags(self):
        digest = build_context_digest(
            "build",
            "3",
            0,
            forensic_verdict={
                "recommendation": "DISTRUST",
                "confidence": 0.42,
                "reward_hacking_flags": ["no_diff", "claim_only"],
            },
        )
        fields = parse(digest)

        assert fields["forensic"] == "DISTRUST(0.42)"
        assert fields["flags"] == "no_diff,claim_only"

    def test_active_loops_are_sorted_and_rendered(self):
        digest = build_context_digest("build", "3", 2, loop_state={"4": 1, "3": 2})

        assert parse(digest)["loops"] == "3:2,4:1"

    def test_candidate_count_is_recorded(self):
        digest = build_context_digest("build", "3", 0, candidate_count=5)

        assert parse(digest)["candidates"] == "5"

    def test_candidate_count_zero_is_recorded(self):
        """Zero candidates is a measurement, not an absence."""
        digest = build_context_digest("build", "3", 0, candidate_count=0)

        assert parse(digest)["candidates"] == "0"


class TestObjectAndDictSources:
    """Context arrives as dicts in some paths and objects in others."""

    def test_reads_attributes_from_objects(self):
        digest = build_context_digest(
            "build",
            "3",
            1,
            step_result=SimpleNamespace(status="UNVERIFIED"),
            previous_envelope=SimpleNamespace(step_id="2", status="VERIFIED"),
        )
        fields = parse(digest)

        assert fields["status"] == "UNVERIFIED"
        assert fields["prev"] == "2:VERIFIED"
