#!/usr/bin/env python3
"""
Tests for Flow Studio UI ID component coverage.

This module validates that key UI regions (header, sidebar, canvas)
have data-uiid attributes for test automation.
"""

import pytest
from tests.flow_studio_ui_ids_helpers import extract_uiids_from_html, get_flow_studio_html


class TestFlowStudioUIIDs:
    """Tests for Flow Studio HTML data-uiid attributes."""

    def test_required_regions_present(self):
        """All required UI regions should have data-uiid."""
        html = get_flow_studio_html()
        uiids = extract_uiids_from_html(html)

        # Extract unique regions from UIIDs
        present_regions = set()
        for uiid, _ in uiids:
            parts = uiid.split(".")
            if len(parts) >= 2:
                region = parts[1].split(":")[0]
                present_regions.add(region)

        # Required regions that must be present
        required = {"header", "sidebar", "canvas", "inspector"}

        missing = required - present_regions
        if missing:
            pytest.fail(f"Missing required UI regions: {', '.join(sorted(missing))}")

    def test_minimum_uiid_coverage(self):
        """Flow Studio should have a minimum number of data-uiid attributes."""
        html = get_flow_studio_html()
        uiids = extract_uiids_from_html(html)

        # We expect at least 25 unique UIIDs for reasonable coverage
        # (Current implementation has 30+ UIIDs)
        MIN_EXPECTED = 25

        if len(uiids) < MIN_EXPECTED:
            pytest.fail(
                f"Only {len(uiids)} data-uiid attributes found, expected at least {MIN_EXPECTED}. "
                "Add data-uiid to key interactive elements."
            )

    def test_header_elements_have_uiids(self):
        """Key header elements should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Expected header UIIDs
        expected_header = [
            "flow_studio.header",
            "flow_studio.header.search",
            "flow_studio.header.mode",
            "flow_studio.header.profile",  # Profile badge
        ]

        missing = [e for e in expected_header if e not in uiids]
        if missing:
            pytest.fail(f"Missing expected header UIIDs: {', '.join(missing)}")

    def test_profile_badge_uiid_exists(self):
        """Profile badge element should have data-uiid for automation."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        uiid = "flow_studio.header.profile"
        assert uiid in uiids, (
            f"Profile badge missing data-uiid='{uiid}'. "
            "This UIID is required for test automation to locate the profile indicator."
        )

    def test_sidebar_elements_have_uiids(self):
        """Key sidebar elements should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Expected sidebar UIIDs
        expected_sidebar = [
            "flow_studio.sidebar",
            "flow_studio.sidebar.run_selector",
            "flow_studio.sidebar.flow_list",
        ]

        missing = [e for e in expected_sidebar if e not in uiids]
        if missing:
            pytest.fail(f"Missing expected sidebar UIIDs: {', '.join(missing)}")

    def test_canvas_elements_have_uiids(self):
        """Key canvas elements should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Expected canvas UIIDs
        expected_canvas = [
            "flow_studio.canvas",
            "flow_studio.canvas.legend",
            "flow_studio.canvas.outline",
        ]

        missing = [e for e in expected_canvas if e not in uiids]
        if missing:
            pytest.fail(f"Missing expected canvas UIIDs: {', '.join(missing)}")


class TestRunHistoryUIIDs:
    """Tests for Run History panel data-uiid attributes."""

    def test_run_history_section_has_uiid(self):
        """Run history section container should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        uiid = "flow_studio.sidebar.run_history"
        assert uiid in uiids, (
            f"Run history section missing data-uiid='{uiid}'. "
            "This UIID is required for test automation to locate the run history panel."
        )

    def test_run_history_filter_has_uiid(self):
        """Run history filter should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        uiid = "flow_studio.sidebar.run_history.filter"
        assert uiid in uiids, (
            f"Run history filter missing data-uiid='{uiid}'. "
            "This UIID is required for test automation to interact with run filtering."
        )

    def test_run_history_list_has_uiid(self):
        """Run history list should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        uiid = "flow_studio.sidebar.run_history.list"
        assert uiid in uiids, (
            f"Run history list missing data-uiid='{uiid}'. "
            "This UIID is required for test automation to locate the list of runs."
        )

    def test_run_history_elements_have_uiids(self):
        """All key run history elements should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Expected run history UIIDs
        expected_run_history = [
            "flow_studio.sidebar.run_history",
            "flow_studio.sidebar.run_history.filter",
            "flow_studio.sidebar.run_history.list",
        ]

        missing = [e for e in expected_run_history if e not in uiids]
        if missing:
            pytest.fail(f"Missing expected run history UIIDs: {', '.join(missing)}")


class TestRunDetailModalUIIDs:
    """Tests for Run Detail modal data-uiid attributes."""

    def test_run_detail_modal_has_uiid(self):
        """Run detail modal container should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        uiid = "flow_studio.modal.run_detail"
        assert uiid in uiids, (
            f"Run detail modal missing data-uiid='{uiid}'. "
            "This UIID is required for test automation to locate the modal."
        )

    def test_run_detail_close_button_has_uiid(self):
        """Run detail modal close button should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        uiid = "flow_studio.modal.run_detail.close"
        assert uiid in uiids, (
            f"Run detail close button missing data-uiid='{uiid}'. "
            "This UIID is required for test automation to close the modal."
        )

    def test_run_detail_body_has_uiid(self):
        """Run detail modal body should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        uiid = "flow_studio.modal.run_detail.body"
        assert uiid in uiids, (
            f"Run detail body missing data-uiid='{uiid}'. "
            "This UIID is required for test automation to read run details."
        )

    def test_run_detail_modal_elements_have_uiids(self):
        """All key run detail modal elements should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Expected run detail modal UIIDs
        expected_modal = [
            "flow_studio.modal.run_detail",
            "flow_studio.modal.run_detail.close",
            "flow_studio.modal.run_detail.body",
            # "flow_studio.modal.run_detail.rerun",  # Dynamic, verified in TestDynamicUIIDs
        ]

        missing = [e for e in expected_modal if e not in uiids]
        if missing:
            pytest.fail(f"Missing expected run detail modal UIIDs: {', '.join(missing)}")

    def test_run_detail_modal_is_dialog(self):
        """Run detail modal should have proper dialog role for accessibility."""
        html = get_flow_studio_html()

        # Find the run detail modal element
        import re

        pattern = re.compile(r'<[^>]*data-uiid="flow_studio\.modal\.run_detail"[^>]*>')
        match = pattern.search(html)
        assert match, "Run detail modal should exist"

        element_html = match.group(0)
        assert 'role="dialog"' in element_html, (
            "Run detail modal should have role='dialog' for accessibility"
        )
        assert 'aria-modal="true"' in element_html, (
            "Run detail modal should have aria-modal='true' for accessibility"
        )
