#!/usr/bin/env python3
"""
A11y regression tests for Flow Studio.

This test suite validates critical accessibility requirements:
1. Landmarks (banner, main, navigation, complementary)
2. ARIA attributes reference valid IDs
3. Interactive elements have accessible names
4. Focus management infrastructure exists
5. Keyboard navigation support

These tests catch common a11y regressions without requiring a browser.
For full WCAG compliance, run axe-core in a browser environment.

See CLAUDE.md § UI Contract for the full accessibility strategy.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import pytest

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


# ============================================================================
# Test Fixtures
# ============================================================================


def get_flow_studio_html() -> str:
    """Load the Flow Studio HTML from the UI module."""
    from swarm.tools.flow_studio_ui import get_index_html

    return get_index_html()


def get_ts_sources() -> Dict[str, str]:
    """Load Flow Studio TypeScript sources for static analysis."""
    sources = {}
    ts_dir = repo_root / "swarm" / "tools" / "flow_studio_ui" / "src"
    for ts_file in ts_dir.glob("*.ts"):
        sources[ts_file.name] = ts_file.read_text(encoding="utf-8")
    return sources


# ============================================================================
# Test Helpers
# ============================================================================


def extract_ids(html: str) -> Set[str]:
    """Extract all id attribute values from HTML."""
    pattern = re.compile(r'\bid="([^"]+)"')
    return set(pattern.findall(html))


def extract_aria_refs(html: str, attr: str) -> List[str]:
    """Extract all references from an aria-* attribute (supports space-separated)."""
    pattern = re.compile(rf'{attr}="([^"]+)"')
    refs = []
    for match in pattern.findall(html):
        refs.extend(match.split())
    return refs


# ============================================================================
# Landmark Tests (WCAG 1.3.1, 2.4.1)
# ============================================================================


class TestLandmarks:
    """Tests for proper landmark structure."""

    def test_has_banner_landmark(self):
        """Page should have a banner landmark (header)."""
        html = get_flow_studio_html()
        # Either <header> or role="banner"
        assert "<header" in html or 'role="banner"' in html, (
            "Page should have a banner landmark for the header region"
        )

    def test_has_main_landmark(self):
        """Page should have a main landmark."""
        html = get_flow_studio_html()
        # Either <main> or role="main"
        assert "<main" in html or 'role="main"' in html, (
            "Page should have a main landmark for primary content"
        )

    def test_has_navigation_landmark(self):
        """Page should have a navigation landmark."""
        html = get_flow_studio_html()
        # Either <nav> or role="navigation"
        assert "<nav" in html or 'role="navigation"' in html, (
            "Page should have a navigation landmark for the sidebar"
        )

    def test_has_complementary_landmark(self):
        """Page should have a complementary landmark (aside/inspector)."""
        html = get_flow_studio_html()
        # Either <aside> or role="complementary"
        assert "<aside" in html or 'role="complementary"' in html, (
            "Page should have a complementary landmark for the inspector panel"
        )


# ============================================================================
# ARIA Reference Tests (WCAG 4.1.2)
# ============================================================================


class TestARIAReferences:
    """Tests for valid ARIA attribute references."""

    def test_aria_labelledby_references_exist(self):
        """All aria-labelledby references should point to existing IDs."""
        html = get_flow_studio_html()
        ids = extract_ids(html)
        refs = extract_aria_refs(html, "aria-labelledby")

        missing = [ref for ref in refs if ref not in ids]
        assert not missing, f"aria-labelledby references non-existent IDs: {missing}"

    def test_aria_controls_references_exist(self):
        """All aria-controls references should point to existing IDs."""
        html = get_flow_studio_html()
        ids = extract_ids(html)
        refs = extract_aria_refs(html, "aria-controls")

        missing = [ref for ref in refs if ref not in ids]
        assert not missing, f"aria-controls references non-existent IDs: {missing}"

    def test_aria_describedby_references_exist(self):
        """All aria-describedby references should point to existing IDs."""
        html = get_flow_studio_html()
        ids = extract_ids(html)
        refs = extract_aria_refs(html, "aria-describedby")

        missing = [ref for ref in refs if ref not in ids]
        assert not missing, f"aria-describedby references non-existent IDs: {missing}"


# ============================================================================
# Modal Accessibility Tests (WCAG 2.4.3)
# ============================================================================


class TestModalAccessibility:
    """Tests for modal dialog accessibility."""

    def test_modals_have_aria_modal(self):
        """Modal dialogs should have aria-modal attribute."""
        html = get_flow_studio_html()

        # Find elements with role="dialog"
        dialog_pattern = re.compile(r'<[^>]*role="dialog"[^>]*>')
        dialogs = dialog_pattern.findall(html)

        for dialog in dialogs:
            assert "aria-modal=" in dialog, (
                f"Dialog should have aria-modal attribute: {dialog[:100]}"
            )

    def test_modals_have_aria_labelledby(self):
        """Modal dialogs should have aria-labelledby for accessible name."""
        html = get_flow_studio_html()

        dialog_pattern = re.compile(r'<[^>]*role="dialog"[^>]*>')
        dialogs = dialog_pattern.findall(html)

        for dialog in dialogs:
            assert "aria-labelledby=" in dialog, (
                f"Dialog should have aria-labelledby: {dialog[:100]}"
            )

    def test_focus_trap_utilities_exist(self):
        """Focus trap utilities should be available for modals."""
        sources = get_ts_sources()
        utils_ts = sources.get("utils.ts", "")

        assert "createFocusTrap" in utils_ts, (
            "Focus trap utility should exist for modal accessibility"
        )

    def test_modal_focus_manager_exists(self):
        """Modal focus manager should be available."""
        sources = get_ts_sources()
        utils_ts = sources.get("utils.ts", "")

        assert "createModalFocusManager" in utils_ts, (
            "Modal focus manager should exist for focus restoration"
        )


# ============================================================================
# Interactive Element Tests (WCAG 4.1.2)
# ============================================================================


class TestInteractiveElements:
    """Tests for accessible interactive elements."""

    def test_buttons_have_accessible_names(self):
        """Buttons should have accessible names (text, aria-label, aria-labelledby, or title)."""
        html = get_flow_studio_html()

        # Find <button> elements
        button_pattern = re.compile(r"<button[^>]*>.*?</button>", re.DOTALL)
        buttons = button_pattern.findall(html)

        for button in buttons:
            # Skip hidden buttons (aria-hidden="true" or hidden attribute)
            if 'aria-hidden="true"' in button or "hidden" in button:
                continue

            # Check for text content (including nested spans)
            # Strip all tags and check for remaining text
            text_only = re.sub(r"<[^>]+>", " ", button)
            text_content = " ".join(text_only.split()).strip()

            has_aria_label = "aria-label=" in button
            has_aria_labelledby = "aria-labelledby=" in button
            has_title = "title=" in button  # title is acceptable fallback

            assert has_aria_label or has_aria_labelledby or text_content or has_title, (
                f"Button should have accessible name: {button[:100]}"
            )

    def test_select_elements_have_labels(self):
        """Select elements should have associated labels."""
        html = get_flow_studio_html()

        # Find all <select> elements with their full opening tag
        select_pattern = re.compile(r"<select[^>]*>")
        selects = select_pattern.findall(html)

        for select_tag in selects:
            # Extract id if present
            id_match = re.search(r'id="([^"]+)"', select_tag)
            select_id = id_match.group(1) if id_match else "unknown"

            # Check for aria-label directly on the element
            has_aria_label = "aria-label=" in select_tag

            # Check for label[for=id] in the HTML
            has_label = False
            if id_match:
                label_pattern = rf'<label[^>]*for="{select_id}"'
                has_label = bool(re.search(label_pattern, html))

            assert has_label or has_aria_label, (
                f"Select '{select_id}' should have an associated label or aria-label"
            )


# ============================================================================
# Keyboard Navigation Tests (WCAG 2.1.1)
# ============================================================================


class TestKeyboardNavigation:
    """Tests for keyboard navigation support."""

    def test_keyboard_shortcuts_documented(self):
        """Keyboard shortcuts should be documented in TypeScript."""
        sources = get_ts_sources()

        assert "shortcuts.ts" in sources, "Shortcuts module should exist for keyboard navigation"

    def test_shortcuts_include_common_keys(self):
        """Common keyboard shortcuts should be implemented."""
        sources = get_ts_sources()
        shortcuts_ts = sources.get("shortcuts.ts", "")
        search_ts = sources.get("search.ts", "")
        all_ts = shortcuts_ts + search_ts

        # Common navigation keys
        assert "Escape" in all_ts, "Escape key should be handled"
        # Enter is handled in search module for form submission
        assert "Enter" in all_ts or "submit" in all_ts.lower(), (
            "Enter key or form submission should be handled"
        )
        assert "?" in shortcuts_ts or "helpKey" in shortcuts_ts.lower(), (
            "Help shortcut (?) should be available"
        )

    def test_search_has_keyboard_shortcut(self):
        """Search should have a keyboard shortcut (/)."""
        sources = get_ts_sources()
        shortcuts_ts = sources.get("shortcuts.ts", "")

        # Search is typically bound to /
        assert '"/"' in shortcuts_ts or "search" in shortcuts_ts.lower(), (
            "Search should have keyboard shortcut"
        )


# ============================================================================
# Status/Live Region Tests (WCAG 4.1.3)
# ============================================================================


class TestLiveRegions:
    """Tests for live region announcements."""

    def test_status_region_exists(self):
        """Page should have a status region for announcements."""
        html = get_flow_studio_html()

        # Either role="status" or aria-live
        has_status = 'role="status"' in html
        has_live = "aria-live=" in html

        assert has_status or has_live, "Page should have a live region for status announcements"

    def test_governance_badge_announces_changes(self):
        """Governance badge should be in a live region."""
        html = get_flow_studio_html()

        # The governance badge area should announce changes
        # Look for role="status" near governance-related elements
        governance_pattern = re.compile(
            r'<[^>]*(governance|selftest)[^>]*role="status"[^>]*>', re.IGNORECASE
        )

        # Also check if there's a general status region
        has_status = 'role="status"' in html

        assert governance_pattern.search(html) or has_status, (
            "Governance status should be announced to assistive technology"
        )


# ============================================================================
# Color/Contrast (WCAG 1.4.3) - Static checks
# ============================================================================


class TestColorAccessibility:
    """Tests for color-related accessibility."""

    def test_css_defines_high_contrast_colors(self):
        """CSS should define color tokens that support adequate contrast."""
        css_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "css" / "flow-studio.base.css"
        if not css_file.exists():
            pytest.skip("CSS file not found")

        css_content = css_file.read_text(encoding="utf-8")

        # Check for color token definitions
        assert "--fs-color-" in css_content, "CSS should use design tokens for consistent colors"

    def test_status_not_color_only(self):
        """Status indicators should not rely on color alone."""
        html = get_flow_studio_html()

        # Status badges should have text or icons, not just color
        # Look for status-related elements
        status_pattern = re.compile(r'<[^>]*class="[^"]*status[^"]*"[^>]*>([^<]*)<')
        matches = status_pattern.findall(html)

        # If we have status elements, they should have text content
        # (This is a heuristic - full check requires visual inspection)
        if matches:
            non_empty = [m for m in matches if m.strip()]
            assert len(non_empty) > 0 or "aria-label" in html, (
                "Status indicators should have text labels, not color alone"
            )


# ============================================================================
# Integration: UI Ready Handshake (for test automation)
# ============================================================================


class TestUIReadyHandshake:
    """Tests for UI readiness handshake (critical for a11y testing with browsers)."""

    def test_ui_ready_attribute_exists(self):
        """HTML should have data-ui-ready attribute for initialization tracking."""
        html = get_flow_studio_html()

        assert "data-ui-ready=" in html, (
            "HTML should have data-ui-ready attribute for readiness tracking. "
            "A11y tools should wait for data-ui-ready='ready' before testing."
        )

    def test_three_state_handshake_documented(self):
        """UI should use three-state handshake (loading/ready/error)."""
        sources = get_ts_sources()

        # Check any TypeScript file for the states
        all_ts = " ".join(sources.values())

        assert '"loading"' in all_ts or "'loading'" in all_ts, "UI should have 'loading' state"
        assert '"ready"' in all_ts or "'ready'" in all_ts, "UI should have 'ready' state"
        assert '"error"' in all_ts or "'error'" in all_ts, "UI should have 'error' state"
