#!/usr/bin/env python3
"""
Tests for Flow Studio UI ID core validation.

This module validates that:
1. All data-uiid attributes follow the naming pattern
2. No duplicate data-uiid values exist
3. UIIDs are stable across loads
"""

import pytest
from tests.flow_studio_ui_ids_helpers import extract_uiids_from_html, get_flow_studio_html, validate_uiid


class TestUIIDPattern:
    """Tests for data-uiid pattern validation."""

    def test_valid_patterns(self):
        """Verify valid patterns are accepted."""
        valid_examples = [
            "flow_studio",  # Root container
            "flow_studio.header",
            "flow_studio.header.search",
            "flow_studio.header.search.input",
            "flow_studio.sidebar.flow_list",
            "flow_studio.canvas.outline",
            "flow_studio.canvas.outline.step:build:1",
            "flow_studio.inspector.properties",
            "flow_studio.modal.selftest",
            "flow_studio.modal.selftest.close",
            "flow_studio.sdlc_bar.flows",
        ]

        for uiid in valid_examples:
            errors = validate_uiid(uiid)
            assert not errors, f"Valid pattern '{uiid}' was rejected: {errors}"

    def test_invalid_patterns_rejected(self):
        """Verify invalid patterns are rejected."""
        invalid_examples = [
            ("header.search", "missing flow_studio prefix"),
            ("FlowStudio.header", "wrong prefix case"),
            ("flow_studio.Header", "uppercase region"),
            ("flow_studio.header.Search", "uppercase component"),
            ("other_app.header", "wrong app prefix"),
        ]

        for uiid, reason in invalid_examples:
            errors = validate_uiid(uiid)
            assert errors, f"Invalid pattern '{uiid}' ({reason}) should be rejected"

    def test_banned_layout_names_rejected(self):
        """Verify layout-based names are rejected."""
        banned_examples = [
            ("flow_studio.header.leftcol", "leftCol"),
            ("flow_studio.header.row2", "row<N>"),
            ("flow_studio.sidebar.column1", "column<N>"),
        ]

        for uiid, expected_pattern in banned_examples:
            errors = validate_uiid(uiid)
            assert any("banned" in e.lower() for e in errors), (
                f"Banned pattern '{uiid}' should be rejected (expected pattern: {expected_pattern})"
            )


class TestFlowStudioUIIDsCore:
    """Core tests for Flow Studio HTML data-uiid attributes."""

    def test_uiids_follow_pattern(self):
        """All data-uiid values should follow the naming pattern."""
        html = get_flow_studio_html()
        uiids = extract_uiids_from_html(html)

        all_errors = []
        for uiid, line in uiids:
            errors = validate_uiid(uiid)
            for error in errors:
                all_errors.append(f"Line {line}: {error}")

        if all_errors:
            error_report = "\n".join(all_errors)
            pytest.fail(f"Invalid data-uiid values found:\n{error_report}")

    def test_no_duplicate_uiids(self):
        """No duplicate data-uiid values should exist."""
        html = get_flow_studio_html()
        uiids = extract_uiids_from_html(html)

        seen: dict[str, int] = {}
        duplicates = []

        for uiid, line in uiids:
            if uiid in seen:
                duplicates.append(f"'{uiid}' appears at lines {seen[uiid]} and {line}")
            else:
                seen[uiid] = line

        if duplicates:
            pytest.fail("Duplicate data-uiid values found:\n" + "\n".join(duplicates))


class TestUIIDConsistency:
    """Tests for UI ID consistency and stability."""

    def test_uiids_are_stable_across_loads(self):
        """data-uiid values should be consistent across multiple loads."""
        html1 = get_flow_studio_html()
        html2 = get_flow_studio_html()

        uiids1 = set(uiid for uiid, _ in extract_uiids_from_html(html1))
        uiids2 = set(uiid for uiid, _ in extract_uiids_from_html(html2))

        assert uiids1 == uiids2, "UIIDs should be identical across loads"

    def test_region_prefix_consistency(self):
        """All UIIDs under a region should start with that region."""
        import re

        html = get_flow_studio_html()
        uiids = extract_uiids_from_html(html)

        inconsistencies = []
        for uiid, line in uiids:
            parts = uiid.split(".")
            if len(parts) < 2:
                continue

            parts[1].split(":")[0]

            # Check that all parts after the region are valid
            for i, part in enumerate(parts[2:], start=2):
                component = part.split(":")[0]
                if not re.match(r"^[a-z][a-z0-9_]*$", component):
                    inconsistencies.append(
                        f"Line {line}: '{uiid}' has invalid component '{component}'"
                    )

        if inconsistencies:
            pytest.fail("UIID consistency errors:\n" + "\n".join(inconsistencies))


class TestAccessibilityIDs:
    """Tests for accessibility-related ID attributes."""

    def test_aria_labelledby_references_exist(self):
        """aria-labelledby references should point to existing IDs."""
        import re

        html = get_flow_studio_html()

        # Find all aria-labelledby references
        labelledby_pattern = re.compile(r'aria-labelledby="([^"]+)"')
        matches = labelledby_pattern.findall(html)

        # Find all IDs in the document
        id_pattern = re.compile(r'\bid="([^"]+)"')
        all_ids = set(id_pattern.findall(html))

        missing = []
        for ref in matches:
            # aria-labelledby can have multiple space-separated IDs
            for id_ref in ref.split():
                if id_ref not in all_ids:
                    missing.append(id_ref)

        if missing:
            pytest.fail(f"aria-labelledby references non-existent IDs: {', '.join(missing)}")

    def test_aria_controls_references_exist(self):
        """aria-controls references should point to existing IDs."""
        import re

        html = get_flow_studio_html()

        # Find all aria-controls references
        controls_pattern = re.compile(r'aria-controls="([^"]+)"')
        matches = controls_pattern.findall(html)

        # Find all IDs in the document
        id_pattern = re.compile(r'\bid="([^"]+)"')
        all_ids = set(id_pattern.findall(html))

        missing = []
        for ref in matches:
            for id_ref in ref.split():
                if id_ref not in all_ids:
                    missing.append(id_ref)

        if missing:
            pytest.fail(f"aria-controls references non-existent IDs: {', '.join(missing)}")
