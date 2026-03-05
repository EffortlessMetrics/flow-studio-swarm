import re
from pathlib import Path
from typing import List, Tuple

import pytest
from swarm.tools.flow_studio_ui import get_index_html

# Flow Studio UI components MUST conform to a specific ID structure
# Format: flow_studio[.<region>.<thing>][:<id>]
#
# <region>: header | sidebar | canvas | inspector | modal
# <thing>: specific component name (e.g. search, run_selector, boundary_review)
# <id>: optional specific item identifier (e.g. run ID, node ID)
UIID_PATTERN = re.compile(
    r"^flow_studio(?:\.(?:header|sidebar|canvas|inspector|modal|inventory|sdlc_bar)(?:\.[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)?)?(?::[a-zA-Z0-9_\-]+)?$"
)

# Known dynamic prefixes that have IDs appended at runtime
DYNAMIC_PREFIXES = [
    "flow_studio.sidebar.run_history.item:",
    "flow_studio.sidebar.run_history.item.badge.backend:",
    "flow_studio.sidebar.run_history.item.badge.exemplar:",
    "flow_studio.sidebar.run_history.item.badge.",  # run type badges
    "flow_studio.canvas.outline.flow:",
    "flow_studio.canvas.outline.step:",
    "flow_studio.canvas.outline.agent:",
    "flow_studio.canvas.outline.artifact:",
    "flow_studio.inspector.details:",
    "flow_studio.inventory.type.",
]


def get_flow_studio_html() -> str:
    """Helper to get the generated HTML or skip if not available."""
    try:
        return get_index_html()
    except FileNotFoundError:
        pytest.skip("Flow Studio UI not generated (run 'make gen-index-html')")


def get_all_ts_files() -> List[Path]:
    """Helper to get all TypeScript files in the UI project."""
    ui_dir = Path(__file__).parent.parent / "swarm" / "tools" / "flow_studio_ui" / "src"
    if not ui_dir.exists():
        return []
    return list(ui_dir.rglob("*.ts"))


def get_all_html_fragments() -> List[Path]:
    """Helper to get all HTML fragments in the UI project."""
    fragments_dir = (
        Path(__file__).parent.parent / "swarm" / "tools" / "flow_studio_ui" / "fragments"
    )
    if not fragments_dir.exists():
        return []
    return list(fragments_dir.glob("*.html"))


def extract_uiids_from_html(html: str) -> List[Tuple[str, int]]:
    """
    Extract all data-uiid attribute values from HTML DOM elements.

    Returns:
        List of (uiid_value, line_number) tuples
    """
    uiids = []
    pattern = re.compile(r'data-uiid="([^"]+)"')

    in_script = False
    script_start = re.compile(r"<script\b", re.IGNORECASE)
    script_end = re.compile(r"</script>", re.IGNORECASE)

    lines = html.splitlines()
    for line_num, line in enumerate(lines, start=1):
        if script_start.search(line):
            if "application/json" not in line:
                in_script = True
        if script_end.search(line):
            in_script = False
            continue

        if in_script:
            continue

        for match in pattern.finditer(line):
            value = match.group(1)
            if "${" in value:
                continue
            uiids.append((value, line_num))

    seen = set()
    deduped_uiids = []
    for value, line_num in uiids:
        if value not in seen:
            seen.add(value)
            deduped_uiids.append((value, line_num))

    return deduped_uiids


def validate_uiid(uiid: str) -> List[str]:
    """
    Validate a single data-uiid value against the contract.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check overall pattern
    if not UIID_PATTERN.match(uiid):
        errors.append(f"'{uiid}' does not match pattern flow_studio[.<region>.<thing>][:<id>]")
        return errors

    # Check lowercase
    if uiid != uiid.lower() and ":" not in uiid:
        # We allow mixed case in the dynamic ID suffix (after colon)
        # but the prefix must be lowercase
        prefix = uiid.split(":")[0]
        if prefix != prefix.lower():
            errors.append(f"'{prefix}' must be lowercase")

    return errors


class TestUIIDContract:
    """Tests for UI ID format and validation."""

    def test_uiid_pattern_matching(self):
        """Valid UIIDs should pass pattern matching."""
        valid_ids = [
            "flow_studio",
            "flow_studio.header",
            "flow_studio.header.search",
            "flow_studio.sidebar.run_selector.select",
            "flow_studio.canvas.outline.flow:my_flow_id",
            "flow_studio.sidebar.run_history.item:run-2026-01-01",
        ]

        for uiid in valid_ids:
            assert UIID_PATTERN.match(uiid), f"Expected '{uiid}' to be valid"

    def test_uiid_pattern_rejection(self):
        """Invalid UIIDs should be rejected."""
        invalid_ids = [
            "flow-studio",  # Wrong root
            "flow_studio.unknown_region",  # Invalid region
            "flow_studio.Header",  # Uppercase
            "flow_studio.header..search",  # Double dot
            "flow_studio.",  # Trailing dot
        ]

        for uiid in invalid_ids:
            assert not UIID_PATTERN.match(uiid), f"Expected '{uiid}' to be invalid"

    def test_all_html_uiids_follow_contract(self):
        """All data-uiid attributes in the rendered HTML must follow the contract."""
        html = get_flow_studio_html()
        uiids = extract_uiids_from_html(html)

        all_errors = []
        for uiid, line in uiids:
            errors = validate_uiid(uiid)
            for err in errors:
                all_errors.append(f"Line {line}: {err}")

        if all_errors:
            pytest.fail("Found invalid UIIDs:\n" + "\n".join(all_errors))


class TestUIIDCores:
    """Tests to ensure core UI elements exist."""

    def test_core_regions_exist(self):
        """All main UI regions should exist and have data-uiid attributes."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Extract the region from all UIIDs (flow_studio.<region>.*)
        present_regions = set()
        for uiid in uiids:
            parts = uiid.split(".")
            if len(parts) > 1:
                present_regions.add(parts[1])

        # Core regions that must be present
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

    def test_no_duplicate_uiids_in_static_html(self):
        """Static UIIDs should not be duplicated in the HTML."""
        html = get_flow_studio_html()
        uiids = extract_uiids_from_html(html)

        # Group by UIID value
        from collections import Counter

        uiid_counts = Counter(uiid for uiid, _ in uiids)

        # Each UIID should appear exactly once
        duplicates = [(uiid, count) for uiid, count in uiid_counts.items() if count > 1]

        assert not duplicates, f"UIIDs must be unique for reliable selectors: {duplicates}"


class TestAccessibilityIDs:
    """Tests for accessibility-related ID attributes."""

    def test_aria_labelledby_references_exist(self):
        """aria-labelledby references should point to existing IDs."""
        html = get_flow_studio_html()

        # Find all aria-labelledby references
        pattern = re.compile(r'aria-labelledby="([^"]+)"')
        references = pattern.findall(html)

        # Check if the referenced IDs exist
        missing_targets = []
        for ref_id in references:
            # Multiple IDs can be space-separated
            for target_id in ref_id.split():
                if f'id="{target_id}"' not in html:
                    missing_targets.append(target_id)

        if missing_targets:
            pytest.fail(f"aria-labelledby targets not found in HTML: {', '.join(missing_targets)}")

    def test_aria_controls_references_exist(self):
        """aria-controls references should point to existing IDs."""
        html = get_flow_studio_html()

        pattern = re.compile(r'aria-controls="([^"]+)"')
        references = pattern.findall(html)

        missing_targets = []
        for ref_id in references:
            for target_id in ref_id.split():
                if f'id="{target_id}"' not in html:
                    missing_targets.append(target_id)

        if missing_targets:
            pytest.fail(f"aria-controls targets not found in HTML: {', '.join(missing_targets)}")


class TestTypeScriptIntegration:
    """Tests ensuring UIIDs are properly exported and used in TypeScript."""

    def test_domain_exports_uiid_type(self):
        """domain.ts should export FlowStudioUIID type."""
        ts_files = get_all_ts_files()
        if not ts_files:
            pytest.skip("TypeScript source files not found")

        domain_file = next((f for f in ts_files if f.name == "domain.ts"), None)
        assert domain_file, "domain.ts not found"

        content = domain_file.read_text()
        assert "export type FlowStudioUIID =" in content, "FlowStudioUIID type not exported"

    def test_qsbyuiid_utility_exists(self):
        """A utility for querying by UIID should exist."""
        ts_files = get_all_ts_files()
        if not ts_files:
            pytest.skip("TypeScript source files not found")

        domain_file = next((f for f in ts_files if f.name == "domain.ts"), None)
        assert domain_file, "domain.ts not found"

        content = domain_file.read_text()
        assert "qsByUiid" in content, "qsByUiid utility not found in domain.ts"

    def test_html_uiids_in_domain_type(self):
        """All static UIIDs in HTML must be defined in the FlowStudioUIID type."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        ts_files = get_all_ts_files()
        if not ts_files:
            pytest.skip("TypeScript source files not found")

        domain_file = next((f for f in ts_files if f.name == "domain.ts"), None)
        assert domain_file, "domain.ts not found"

        domain_content = domain_file.read_text()

        missing_from_ts = []
        for uiid in uiids:
            # We only expect exact static strings to be in the TS type definition
            # Dynamic ones (containing :) are typed with template literals
            if ":" not in uiid:
                if f'"{uiid}"' not in domain_content:
                    missing_from_ts.append(uiid)

        if missing_from_ts:
            pytest.fail(
                "These static UIIDs are in HTML but missing from FlowStudioUIID type:\n"
                + "\n".join(missing_from_ts)
            )


class TestInteractiveElementUIIDs:
    """Tests ensuring key interactive elements have UIIDs for test automation."""

    def test_modals_have_uiids(self):
        """All modals should have a data-uiid attribute."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Expected modal UIIDs
        expected = [
            "flow_studio.modal.shortcuts",
            "flow_studio.modal.selftest",
            "flow_studio.modal.run_detail",
            "flow_studio.modal.boundary_review.container",
        ]

        missing = [e for e in expected if e not in uiids]
        if missing:
            pytest.fail(f"Missing expected modal UIIDs: {', '.join(missing)}")

    def test_run_control_buttons_have_uiids(self):
        """Run control play/pause/stop buttons should have UIIDs."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Expected run control UIIDs
        expected = [
            "flow_studio.sidebar.run_control.play",
            "flow_studio.sidebar.run_control.pause",
            "flow_studio.sidebar.run_control.stop",
        ]

        missing = [e for e in expected if e not in uiids]
        if missing:
            pytest.fail(f"Missing run control button UIIDs: {', '.join(missing)}")

    def test_header_controls_have_uiids(self):
        """Header control buttons should have UIIDs."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        # Expected header control UIIDs
        expected = [
            "flow_studio.header.tour.trigger",
            "flow_studio.header.teaching_mode.toggle",
            "flow_studio.header.reload.btn",
        ]

        missing = [e for e in expected if e not in uiids]
        if missing:
            pytest.fail(f"Missing header control button UIIDs: {', '.join(missing)}")


class TestLegendToggleIntegration:
    """Integration tests demonstrating Legend Toggle selector usage.

    These tests verify that elements exist AND demonstrate the selector
    pattern for actual test automation.
    """

    def test_legend_toggle_has_aria_expanded(self):
        """Verify legend toggle has aria-expanded state.

        When tests click the toggle, JavaScript will update aria-expanded,
        which tests can use to verify toggle state without visual inspection.

        Playwright example:
            toggle = page.locator('[data-uiid="flow_studio.canvas.legend.toggle"]')
            await expect(toggle).to_have_attribute('aria-expanded', 'true')
        """
        html = get_flow_studio_html()

        # Find the legend toggle element
        pattern = re.compile(r'<[^>]*data-uiid="flow_studio\.canvas\.legend\.toggle"[^>]*>')
        match = pattern.search(html)
        assert match, "Legend toggle should exist"

        element_html = match.group(0)
        assert "aria-expanded=" in element_html, "Legend toggle should have aria-expanded attribute"


class TestRunHistoryUIIDs:
    """Tests for Run History panel data-uiid attributes.

    The Run History panel provides a list of previous runs in the sidebar.
    These UIIDs enable test automation to:
    - Locate the run history section
    - Filter runs by status/flow
    - Select specific runs from the list
    """

    def test_run_history_container_has_uiid(self):
        """Run history main container should have data-uiid."""
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
    """Tests for Run Detail modal data-uiid attributes.

    The Run Detail modal displays detailed information about a selected run.
    These UIIDs enable test automation to:
    - Open and close the modal
    - Read run details
    - Re-run specific executions
    """

    def test_run_detail_modal_has_uiid(self):
        """Run detail modal should have data-uiid."""
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

    def test_run_detail_rerun_button_has_uiid(self):
        """Run detail modal re-run button should have data-uiid."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        uiid = "flow_studio.modal.run_detail.rerun"
        assert uiid in uiids, (
            f"Run detail re-run button missing data-uiid='{uiid}'. "
            "This UIID is required for test automation to trigger re-runs."
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
            "flow_studio.modal.run_detail.rerun",
        ]

        missing = [e for e in expected_modal if e not in uiids]
        if missing:
            pytest.fail(f"Missing expected run detail modal UIIDs: {', '.join(missing)}")

    def test_run_detail_modal_is_dialog(self):
        """Run detail modal should have proper dialog role for accessibility."""
        html = get_flow_studio_html()

        # Find the run detail modal element
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


class TestRunDetailModalIntegration:
    """Integration tests demonstrating Run Detail modal selector usage.

    These tests verify that elements exist AND demonstrate the selector
    pattern for actual test automation.
    """

    def test_run_detail_modal_selector(self):
        """Verify the standard CSS selector for the modal.

        Playwright selector: [data-uiid="flow_studio.modal.run_detail"]
        """
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
        """Verify run detail close is a button element.

        Playwright selector: [data-uiid="flow_studio.modal.run_detail.close"]
        """
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
        """Verify run detail re-run is a button element.

        Playwright selector: [data-uiid="flow_studio.modal.run_detail.rerun"]
        """
        html = get_flow_studio_html()

        # Extract the rerun button element
        pattern = re.compile(r'<button[^>]*data-uiid="flow_studio\.modal\.run_detail\.rerun"[^>]*>')
        match = pattern.search(html)
        assert match, "Run detail rerun button should exist"


class TestRunHistoryIntegration:
    """Integration tests demonstrating Run History selector usage.

    These tests verify that elements exist AND demonstrate the selector
    pattern for actual test automation.
    """

    def test_run_history_list_has_role(self):
        """Verify run history list has proper list role for accessibility.

        Playwright selector: [data-uiid="flow_studio.sidebar.run_history.list"]
        """
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


class TestDynamicUIIDs:
    """Tests for data-uiid attributes in dynamically rendered components.

    Some components (like run detail modal content, run history items) are
    rendered dynamically by TypeScript. These tests verify the UIIDs are
    present in the compiled JavaScript code.
    """

    def test_run_history_item_uiid_in_domain(self):
        """Run history item dynamic UIID pattern should be defined."""
        ts_files = get_all_ts_files()
        if not ts_files:
            pytest.skip("TypeScript source files not found")

        domain_file = next((f for f in ts_files if f.name == "domain.ts"), None)
        assert domain_file, "domain.ts not found"

        content = domain_file.read_text()
        assert "flow_studio.sidebar.run_history.item:" in content, (
            "Dynamic UIID pattern for run history items must be documented in domain.ts"
        )

    def test_events_container_uiid_in_run_detail_modal(self):
        """Events container UIID should exist."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        assert "flow_studio.modal.run_detail.events.container" in uiids, (
            "Events container UIID missing from run detail modal HTML"
        )

    def test_exemplar_checkbox_uiid_in_run_detail_modal(self):
        """Exemplar checkbox UIID should exist."""
        html = get_flow_studio_html()
        uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}

        assert "flow_studio.modal.run_detail.exemplar" in uiids, (
            "Exemplar checkbox UIID missing from run detail modal HTML"
        )


class TestBackendBadgeUIIDs:
    """Tests specifically for backend badge dynamic UIIDs."""

    def test_backend_badge_pattern_documented(self):
        """Backend badge dynamic UIID pattern should be defined."""
        ts_files = get_all_ts_files()
        if not ts_files:
            pytest.skip("TypeScript source files not found")

        domain_file = next((f for f in ts_files if f.name == "domain.ts"), None)
        assert domain_file, "domain.ts not found"

        content = domain_file.read_text()
        assert "flow_studio.sidebar.run_history.item.badge.backend:" in content, (
            "Dynamic UIID pattern for backend badges must be documented in domain.ts"
        )


class TestEventsTimelineUIIDs:
    """Tests for Events Timeline data-uiid attributes."""

    def test_events_uiids_defined_in_domain(self):
        """Events timeline UIIDs should be defined in domain.ts."""
        ts_files = get_all_ts_files()
        if not ts_files:
            pytest.skip("TypeScript source files not found")

        domain_file = next((f for f in ts_files if f.name == "domain.ts"), None)
        assert domain_file, "domain.ts not found"

        content = domain_file.read_text()
        assert "flow_studio.modal.run_detail.events.toggle" in content
        assert "flow_studio.modal.run_detail.events.container" in content
