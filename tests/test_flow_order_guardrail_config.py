"""
Configuration tests for the flow order guardrail.

This module tests the allowlist and exclusion configuration for the
flow order guardrail.
"""

from pathlib import Path
from typing import List, Tuple

import pytest

from tests.test_flow_order_guardrail import (
    ALLOWED_VIOLATIONS,
    EXCLUDE_PATTERNS,
    FLOW_LIST_6_PATTERN,
    FLOW_LIST_7_PATTERN,
    FLOW_LIST_START_PATTERN,
    FLOW_TUPLE_START_PATTERN,
    _get_project_root,
    _should_exclude,
)


class TestFlowOrderGuardrailExclusions:
    """Test that exclusion patterns work correctly."""

    def test_test_files_are_excluded(self):
        """Test files should be excluded from scanning."""
        assert _should_exclude(Path("tests/test_flow_registry.py"))
        assert _should_exclude(Path("swarm/tools/test_gen_adapters.py"))

    def test_pycache_is_excluded(self):
        """__pycache__ directories should be excluded."""
        assert _should_exclude(Path("swarm/api/__pycache__/routes.cpython-311.pyc"))

    def test_archive_is_excluded(self):
        """Archive directories should be excluded."""
        assert _should_exclude(Path("swarm/tools/_archive/old_code.py"))

    def test_production_files_are_not_excluded(self):
        """Normal production files should not be excluded."""
        assert not _should_exclude(Path("swarm/api/routes/runs.py"))
        assert not _should_exclude(Path("swarm/runtime/orchestrator.py"))
        assert not _should_exclude(Path("swarm/config/flow_registry.py"))


class TestFlowOrderGuardrailAllowlist:
    """Test that the allowlist is valid and well-maintained."""

    def test_allowlist_files_exist(self):
        """All files in ALLOWED_VIOLATIONS should exist."""
        project_root = _get_project_root()
        missing_files = []

        for relative_path in ALLOWED_VIOLATIONS.keys():
            full_path = project_root / relative_path
            if not full_path.exists():
                missing_files.append(relative_path)

        if missing_files:
            msg = (
                "Stale entries in ALLOWED_VIOLATIONS - files no longer exist:\n"
                + "\n".join(f"  - {f}" for f in missing_files)
                + "\n\nRemove these entries from ALLOWED_VIOLATIONS."
            )
            pytest.fail(msg)

    def test_allowlist_lines_still_have_violations(self):
        """Allowed lines should still contain the violation pattern.

        This prevents stale allowlist entries from accumulating when
        the underlying code is refactored.
        """
        project_root = _get_project_root()
        stale_entries: List[Tuple[str, int, str]] = []

        for relative_path, line_numbers in ALLOWED_VIOLATIONS.items():
            full_path = project_root / relative_path
            if not full_path.exists():
                continue  # Already caught by test_allowlist_files_exist

            try:
                content = full_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Check each allowed line number
            lines = content.split("\n")
            for line_num, justification in line_numbers.items():
                if line_num > len(lines):
                    stale_entries.append((relative_path, line_num, "Line number out of range"))
                    continue

                line = lines[line_num - 1]  # Convert to 0-based index

                # Check if this line still has a flow list pattern
                has_pattern = any(
                    p.search(line)
                    for p in [
                        FLOW_LIST_START_PATTERN,
                        FLOW_LIST_6_PATTERN,
                        FLOW_LIST_7_PATTERN,
                        FLOW_TUPLE_START_PATTERN,
                    ]
                )

                if not has_pattern:
                    stale_entries.append(
                        (
                            relative_path,
                            line_num,
                            f"No flow list pattern found (justification: {justification})",
                        )
                    )

        if stale_entries:
            msg = "Stale entries in ALLOWED_VIOLATIONS - lines no longer have flow lists:\n"
            for path, line_num, reason in stale_entries:
                msg += f"  - {path}:{line_num} - {reason}\n"
            msg += "\nRemove these stale entries from ALLOWED_VIOLATIONS."
            pytest.fail(msg)

    def test_allowlist_has_justifications(self):
        """All allowlist entries should have non-empty justifications."""
        missing_justifications = []

        for relative_path, line_numbers in ALLOWED_VIOLATIONS.items():
            for line_num, justification in line_numbers.items():
                if not justification or not justification.strip():
                    missing_justifications.append((relative_path, line_num))

        if missing_justifications:
            msg = "ALLOWED_VIOLATIONS entries missing justifications:\n"
            for path, line_num in missing_justifications:
                msg += f"  - {path}:{line_num}\n"
            msg += "\nAll allowlist entries must have a justification explaining why the hardcoded list is acceptable."
            pytest.fail(msg)
