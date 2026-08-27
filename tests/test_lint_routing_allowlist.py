"""
Tests for the deprecation-doc allowlist in swarm/tools/lint_routing_fields.py.

The bare-mention warning patterns ask the reader to "verify this is deprecation
documentation". A handful of files *are* that documentation, so naming the
retired `route_to_flow` / `route_to_agent` fields is their whole purpose.

The allowlist must suppress those warnings without also suppressing a genuine
reintroduction of the retired fields, which remains an error.
"""

import pytest
from swarm.tools.lint_routing_fields import (
    DEPRECATION_DOC_ALLOWLIST,
    check_file,
    is_deprecation_doc,
)


@pytest.fixture
def allowlisted_file(tmp_path):
    """A file at an allowlisted path."""
    target = tmp_path / "docs" / "RELEASE_CHECKLIST.md"
    target.parent.mkdir(parents=True)
    return target


@pytest.fixture
def ordinary_file(tmp_path):
    """A file at a path that is not allowlisted."""
    target = tmp_path / "docs" / "SOME_OTHER_DOC.md"
    target.parent.mkdir(parents=True)
    return target


class TestAllowlistMembership:
    """Tests for allowlist path matching."""

    def test_allowlist_entries_carry_justifications(self):
        """Every allowlisted path documents why it names the retired fields."""
        for path, justification in DEPRECATION_DOC_ALLOWLIST.items():
            assert justification.strip(), f"{path} has no justification"

    def test_allowlisted_path_matches(self, allowlisted_file):
        """A path ending in an allowlisted suffix is recognised."""
        assert is_deprecation_doc(allowlisted_file)

    def test_ordinary_path_does_not_match(self, ordinary_file):
        """An unrelated path is not allowlisted."""
        assert not is_deprecation_doc(ordinary_file)

    def test_allowlisted_files_exist_in_repo(self):
        """Allowlist entries point at files that actually exist.

        A stale entry silently widens the allowlist, so entries must be
        removed when the file they cover is deleted or moved.
        """
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[1]
        missing = [path for path in DEPRECATION_DOC_ALLOWLIST if not (repo_root / path).exists()]

        assert not missing, f"Stale DEPRECATION_DOC_ALLOWLIST entries: {missing}"


class TestWarningSuppression:
    """Tests that bare mentions are suppressed only where allowlisted."""

    def test_bare_mention_warns_in_ordinary_file(self, ordinary_file):
        """An unexplained mention of a retired field still warns."""
        ordinary_file.write_text("The old route_to_flow field is gone.\n", encoding="utf-8")

        violations, _ = check_file(ordinary_file)

        assert [v for v in violations if v.is_warning]

    def test_bare_mention_is_silent_in_allowlisted_file(self, allowlisted_file):
        """The same mention in deprecation documentation is not flagged."""
        allowlisted_file.write_text("The old route_to_flow field is gone.\n", encoding="utf-8")

        violations, _ = check_file(allowlisted_file)

        assert not violations


class TestErrorsStillFire:
    """Tests that the allowlist never downgrades a real violation."""

    def test_numeric_route_to_flow_is_an_error_even_when_allowlisted(self, allowlisted_file):
        """Reintroducing `route_to_flow: <n>` errors inside an allowlisted file."""
        allowlisted_file.write_text("route_to_flow: 3\n", encoding="utf-8")

        violations, _ = check_file(allowlisted_file)
        errors = [v for v in violations if not v.is_warning]

        assert errors, "allowlist must not suppress legacy violation patterns"

    def test_route_to_agent_is_an_error_even_when_allowlisted(self, allowlisted_file):
        """Reintroducing `route_to_agent: <agent>` errors inside an allowlisted file."""
        allowlisted_file.write_text("route_to_agent: code-critic\n", encoding="utf-8")

        violations, _ = check_file(allowlisted_file)
        errors = [v for v in violations if not v.is_warning]

        assert errors, "allowlist must not suppress legacy violation patterns"
