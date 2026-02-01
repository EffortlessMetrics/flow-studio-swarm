#!/usr/bin/env python3
"""
Tests for Flow Studio UI ID integration and dynamic content.

This module validates selector usage examples and dynamically rendered
UI components.
"""

from pathlib import Path
import re
import pytest
from tests.flow_studio_ui_ids_helpers import extract_uiids_from_html, get_flow_studio_html

# Add repo root to path so swarm imports work
import sys
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


class TestUIIDSelectorUsage:
    """Tests demonstrating how to locate elements using data-uiid selectors."""

    def test_locate_search_input_by_uiid(self):
        """Demonstrate locating search input by data-uiid."""
        html = get_flow_studio_html()

        # This is the recommended way to locate the search input
        uiid = "flow_studio.header.search.input"
        pattern = f'data-uiid="{uiid}"'

        assert pattern in html, f"Search input with data-uiid={uiid} should exist"

        # Also verify it has expected attributes
        assert 'id="search-input"' in html, "Search input should have id for backwards compat"

    def test_locate_run_selector_by_uiid(self):
        """Demonstrate locating run selector by data-uiid."""
        html = get_flow_studio_html()

        # This is the recommended way to locate the run selector
        uiid = "flow_studio.sidebar.run_selector.select"
        pattern = f'data-uiid="{uiid}"'

        assert pattern in html, f"Run selector with data-uiid={uiid} should exist"

    def test_locate_flow_list_by_uiid(self):
        """Demonstrate locating flow list by data-uiid."""
        html = get_flow_studio_html()

        # This is the recommended way to locate the flow list
        uiid = "flow_studio.sidebar.flow_list"
        pattern = f'data-uiid="{uiid}"'

        assert pattern in html, f"Flow list with data-uiid={uiid} should exist"

    def test_uiid_selectors_are_unique(self):
        """Verify each data-uiid can uniquely identify an element."""
        html = get_flow_studio_html()
        uiids = extract_uiids_from_html(html)

        # Group by UIID value
        from collections import Counter

        uiid_counts = Counter(uiid for uiid, _ in uiids)

        # Each UIID should appear exactly once
        duplicates = [(uiid, count) for uiid, count in uiid_counts.items() if count > 1]

        assert not duplicates, f"UIIDs must be unique for reliable selectors: {duplicates}"


class TestUIIDIntegrationExample:
    """Integration test examples showing real data-uiid usage."""

    def test_search_input_selector_integration(self):
        """Verify search input can be reliably located by data-uiid."""
        html = get_flow_studio_html()

        # Build the actual CSS selector pattern
        selector = '[data-uiid="flow_studio.header.search.input"]'

        # Verify the element exists with this selector
        assert selector.replace('[data-uiid="', 'data-uiid="').replace('"]', '"') in html

        # Extract the element's id for backwards-compatibility check
        pattern = re.compile(r'<input[^>]*data-uiid="flow_studio\.header\.search\.input"[^>]*>')
        match = pattern.search(html)
        assert match, "Search input element should exist with data-uiid"

        element_html = match.group(0)
        assert 'id="search-input"' in element_html, (
            "Search input should have legacy id for backwards compatibility"
        )

    def test_run_selector_css_selector(self):
        """Verify run selector dropdown can be reliably located by data-uiid."""
        html = get_flow_studio_html()

        # The recommended CSS selector for test automation
        css_selector = '[data-uiid="flow_studio.sidebar.run_selector.select"]'

        # Extract the actual <select> element
        pattern = re.compile(
            r'<select[^>]*data-uiid="flow_studio\.sidebar\.run_selector\.select"[^>]*>'
        )
        match = pattern.search(html)
        assert match, f"Element with selector {css_selector} should exist"

        # Verify it's a <select> element (important for automation)
        element_html = match.group(0)
        assert element_html.startswith("<select"), "Run selector should be a <select> element"

    def test_mode_toggle_buttons_by_uiid(self):
        """Verify mode toggle buttons can be located by data-uiid."""
        html = get_flow_studio_html()

        # Both mode buttons should exist
        for mode in ["author", "operator"]:
            uiid = f"flow_studio.header.mode.{mode}"
            css_selector = f'[data-uiid="{uiid}"]'

            # Verify the pattern exists
            assert f'data-uiid="{uiid}"' in html, (
                f"Mode button with selector {css_selector} should exist"
            )

    def test_legend_toggle_has_aria_expanded(self):
        """Verify legend toggle has aria-expanded for state tracking."""
        html = get_flow_studio_html()

        # Find the legend toggle element
        pattern = re.compile(r'<[^>]*data-uiid="flow_studio\.canvas\.legend\.toggle"[^>]*>')
        match = pattern.search(html)
        assert match, "Legend toggle should exist"

        element_html = match.group(0)
        assert "aria-expanded=" in element_html, "Legend toggle should have aria-expanded attribute"


class TestRunDetailModalIntegration:
    """Integration tests demonstrating Run Detail modal selector usage."""

    def test_run_detail_modal_css_selector(self):
        """Verify run detail modal can be reliably located by data-uiid."""
        html = get_flow_studio_html()

        # The recommended CSS selector for test automation
        css_selector = '[data-uiid="flow_studio.modal.run_detail"]'

        # Extract the actual element
        pattern = re.compile(r'<div[^>]*data-uiid="flow_studio\.modal\.run_detail"[^>]*>')
        match = pattern.search(html)
        assert match, f"Element with selector {css_selector} should exist"

        # Verify it's a div element with proper dialog attributes
        element_html = match.group(0)
        assert 'role="dialog"' in element_html, "Run detail modal should be a dialog"

    def test_run_detail_close_is_button(self):
        """Verify run detail close is a button element."""
        html = get_flow_studio_html()

        # Extract the close button element
        pattern = re.compile(r'<button[^>]*data-uiid="flow_studio\.modal\.run_detail\.close"[^>]*>')
        match = pattern.search(html)
        assert match, "Run detail close button should exist"

        element_html = match.group(0)
        assert "aria-label=" in element_html, (
            "Close button should have aria-label for accessibility"
        )

    def test_run_detail_rerun_is_button(self):
        """Verify run detail re-run is a button element."""
        html = get_flow_studio_html()

        # Extract the rerun button element
        pattern = re.compile(r'<button[^>]*data-uiid="flow_studio\.modal\.run_detail\.rerun"[^>]*>')
        match = pattern.search(html)
        assert match, "Run detail rerun button should exist"


class TestRunHistoryIntegration:
    """Integration tests demonstrating Run History selector usage."""

    def test_run_history_list_has_role(self):
        """Verify run history list has proper list role for accessibility."""
        html = get_flow_studio_html()

        # Extract the run history list element
        pattern = re.compile(r'<div[^>]*data-uiid="flow_studio\.sidebar\.run_history\.list"[^>]*>')
        match = pattern.search(html)
        assert match, "Run history list should exist"

        element_html = match.group(0)
        assert 'role="list"' in element_html, (
            "Run history list should have role='list' for accessibility"
        )

    def test_run_history_list_has_aria_label(self):
        """Verify run history list has aria-label for accessibility."""
        html = get_flow_studio_html()

        # Extract the run history list element
        pattern = re.compile(r'<div[^>]*data-uiid="flow_studio\.sidebar\.run_history\.list"[^>]*>')
        match = pattern.search(html)
        assert match, "Run history list should exist"

        element_html = match.group(0)
        assert "aria-label=" in element_html, (
            "Run history list should have aria-label for accessibility"
        )


# Dynamic tests moved to tests/test_flow_studio_ui_ids_dynamic.py
