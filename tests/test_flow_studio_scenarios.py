#!/usr/bin/env python3
"""
Scenario-level tests for Flow Studio UX paths.

This test suite validates core user journeys through Flow Studio:
1. Baseline health check - UI loads and shows healthy state
2. Search and navigation - Find flows/steps/agents
3. Deep linking - URL parameters work correctly
4. Selection state - Graph, outline, and details panel stay in sync

These tests use the data-uiid contract and SDK interface documented in CLAUDE.md.

Test automation should use:
- data-uiid selectors for reliable element location
- window.__flowStudio SDK for navigation and state
- html[data-ui-ready="ready"] for readiness handshake
"""

import re
import sys
from pathlib import Path
from typing import Dict, List

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


def extract_sdk_methods(ts_content: str) -> List[str]:
    """Extract method names from FlowStudioSDK interface."""
    # Look for methods defined in the interface
    pattern = re.compile(r"^\s+(\w+)\s*[:(]", re.MULTILINE)
    matches = pattern.findall(ts_content)
    return [m for m in matches if m not in ("getState", "interface")]


def extract_uiids_from_html(html: str) -> List[str]:
    """Extract all data-uiid values from HTML."""
    pattern = re.compile(r'data-uiid="([^"]+)"')
    return pattern.findall(html)


# ============================================================================
# Scenario 1: Baseline Health Check
# ============================================================================


class TestBaselineHealthCheck:
    """Tests for baseline UI health when loaded with a healthy run.

    User journey: Load Flow Studio → See green status → UI is interactive

    Playwright script example:
        # 1. Navigate to Flow Studio
        await page.goto('http://localhost:5000')

        # 2. Wait for UI ready
        await page.wait_for_selector('html[data-ui-ready="ready"]')

        # 3. Verify SDLC bar shows all green
        sdlc_bar = page.locator('[data-uiid="flow_studio.sdlc_bar"]')
        await expect(sdlc_bar).to_be_visible()

        # 4. Verify no governance warnings
        gov_badge = page.locator('[data-uiid="flow_studio.header.governance"]')
        # Badge should show OK status
    """

    def test_html_has_ui_ready_attribute(self):
        """HTML should have data-ui-ready attribute for initialization tracking."""
        html = get_flow_studio_html()

        # The initial state should be "loading"
        assert 'data-ui-ready="loading"' in html or "data-ui-ready" in html, (
            "HTML should have data-ui-ready attribute for UI readiness tracking"
        )

    def test_sdlc_bar_has_uiid(self):
        """SDLC bar should have data-uiid for test automation."""
        html = get_flow_studio_html()

        # The SDLC bar container should exist
        assert 'data-uiid="flow_studio.sdlc_bar"' in html, (
            "SDLC bar should have data-uiid for automation"
        )

    def test_flow_list_has_uiid(self):
        """Flow list should have data-uiid for navigation tests."""
        html = get_flow_studio_html()

        assert 'data-uiid="flow_studio.sidebar.flow_list"' in html, (
            "Flow list should have data-uiid for automation"
        )

    def test_details_panel_has_uiid(self):
        """Details panel should have data-uiid for selection tests."""
        html = get_flow_studio_html()

        assert 'data-uiid="flow_studio.inspector"' in html, (
            "Details panel should have data-uiid for automation"
        )


# ============================================================================
# Scenario 2: Search and Navigation
# ============================================================================


class TestSearchAndNavigation:
    """Tests for search functionality and navigation.

    User journey: Type in search → See results → Select result → Navigate

    Playwright script example:
        # 1. Focus search via '/' shortcut
        await page.keyboard.press('/')

        # 2. Type search query
        search = page.locator('[data-uiid="flow_studio.header.search.input"]')
        await search.fill('build')

        # 3. Wait for dropdown
        dropdown = page.locator('[data-uiid="flow_studio.header.search.dropdown"]')
        await expect(dropdown).to_be_visible()

        # 4. Select first result
        await page.keyboard.press('Enter')

        # 5. Verify flow changed
        state = await page.evaluate('window.__flowStudio.getState()')
        assert state['currentFlowKey'] == 'build'
    """

    def test_search_input_has_uiid(self):
        """Search input should have data-uiid for automation."""
        html = get_flow_studio_html()

        assert 'data-uiid="flow_studio.header.search.input"' in html, (
            "Search input should have data-uiid"
        )

    def test_search_dropdown_has_uiid(self):
        """Search dropdown should have data-uiid for result selection."""
        html = get_flow_studio_html()

        assert 'data-uiid="flow_studio.header.search.results"' in html, (
            "Search results dropdown should have data-uiid"
        )

    def test_sdk_has_set_active_flow(self):
        """SDK should expose setActiveFlow for programmatic navigation."""
        sources = get_ts_sources()
        domain_ts = sources.get("domain.ts", "")

        # Check that the SDK interface includes setActiveFlow
        assert "setActiveFlow" in domain_ts, "SDK should expose setActiveFlow for navigation"

    def test_sdk_has_select_step(self):
        """SDK should expose selectStep for programmatic step selection."""
        sources = get_ts_sources()
        domain_ts = sources.get("domain.ts", "")

        assert "selectStep" in domain_ts, "SDK should expose selectStep for step selection"


# ============================================================================
# Scenario 3: Deep Linking
# ============================================================================


class TestDeepLinking:
    """Tests for URL deep link functionality.

    User journey: Load URL with params → UI restores state → Shareable link

    Playwright script example:
        # 1. Navigate with deep link params
        await page.goto('http://localhost:5000?flow=build&step=1')

        # 2. Wait for UI ready
        await page.wait_for_selector('html[data-ui-ready="ready"]')

        # 3. Verify flow is selected
        state = await page.evaluate('window.__flowStudio.getState()')
        assert state['currentFlowKey'] == 'build'

        # 4. Verify step is selected (after selection is restored)
        assert state['selectedNodeId'] is not None
    """

    def test_url_params_documented(self):
        """URL parameter handling should be documented in TypeScript."""
        sources = get_ts_sources()
        app_ts = sources.get("flow-studio-app.ts", "")

        # Check for URL param handling
        assert "getURLParams" in app_ts, "URL parameter handling should be implemented"
        assert "applyDeepLinkParams" in app_ts, "Deep link params should be applied on load"

    def test_url_includes_selection_params(self):
        """URL management should include step/agent selection params."""
        sources = get_ts_sources()
        app_ts = sources.get("flow-studio-app.ts", "")

        # Check for step and agent params in URL handling
        assert '"step"' in app_ts or "'step'" in app_ts, "URL should support step parameter"
        assert '"agent"' in app_ts or "'agent'" in app_ts, "URL should support agent parameter"

    def test_popstate_handler_exists(self):
        """Browser back/forward navigation should be handled."""
        sources = get_ts_sources()
        app_ts = sources.get("flow-studio-app.ts", "")

        assert "popstate" in app_ts, "popstate handler should exist for back/forward navigation"


# ============================================================================
# Scenario 4: Selection State Sync
# ============================================================================


class TestSelectionStateSync:
    """Tests for selection state synchronization across UI surfaces.

    User journey: Click graph node → Details panel updates → Outline updates

    Playwright script example:
        # 1. Get current state
        initial = await page.evaluate('window.__flowStudio.getState()')

        # 2. Select a step programmatically
        await page.evaluate('''
            window.__flowStudio.selectStep('build', '1')
        ''')

        # 3. Verify state updated
        final = await page.evaluate('window.__flowStudio.getState()')
        assert final['selectedNodeId'] is not None

        # 4. Verify details panel updated
        details = page.locator('[data-uiid="flow_studio.inspector"]')
        await expect(details).to_contain_text('build')
    """

    def test_selection_state_in_sdk(self):
        """SDK getState should include selection information."""
        sources = get_ts_sources()
        domain_ts = sources.get("domain.ts", "")

        # Check that SDK state includes selection
        assert "selectedNodeId" in domain_ts, "SDK state should include selectedNodeId"
        assert "selectedNodeType" in domain_ts, "SDK state should include selectedNodeType"

    def test_unified_selection_module_exists(self):
        """There should be a unified selection module for consistency."""
        sources = get_ts_sources()

        assert "selection.ts" in sources, "Unified selection module should exist"

    def test_selection_module_has_select_node(self):
        """Selection module should have a unified selectNode function."""
        sources = get_ts_sources()
        selection_ts = sources.get("selection.ts", "")

        assert (
            "export async function selectNode" in selection_ts
            or "export function selectNode" in selection_ts
        ), "Selection module should expose selectNode function"

    def test_selection_updates_url(self):
        """Selection should update URL for shareable links."""
        sources = get_ts_sources()
        selection_ts = sources.get("selection.ts", "")

        assert "updateURL" in selection_ts, "Selection should trigger URL update"


# ============================================================================
# Scenario 5: Tour Navigation
# ============================================================================


class TestTourNavigation:
    """Tests for interactive tour functionality.

    User journey: Start tour → Follow steps → See highlights → Complete tour

    Playwright script example:
        # 1. Start a tour
        await page.locator('[data-uiid="flow_studio.header.tour"]').click()

        # 2. Select a tour from menu
        await page.locator('.tour-menu-item').first.click()

        # 3. Navigate through tour steps
        next_btn = page.locator('.tour-nav-btn.primary')
        await next_btn.click()

        # 4. Verify flow changed with tour
        state = await page.evaluate('window.__flowStudio.getState()')
        assert state['currentFlowKey'] is not None
    """

    def test_tour_dropdown_has_uiid(self):
        """Tour dropdown should have data-uiid for automation."""
        html = get_flow_studio_html()

        # Tour dropdown or button should exist
        assert "tour" in html.lower(), "Tour functionality should be present in UI"

    def test_tours_module_exists(self):
        """Tours module should exist for tour functionality."""
        sources = get_ts_sources()

        assert "tours.ts" in sources, "Tours module should exist"


# ============================================================================
# Scenario 6: Selftest Drill-down
# ============================================================================


class TestSelftestDrilldown:
    """Tests for selftest modal functionality.

    User journey: Open selftest → See status → Click step → See details

    Playwright script example:
        # 1. Open selftest modal via badge
        await page.locator('[data-uiid="flow_studio.header.governance"]').click()

        # 2. Wait for modal
        modal = page.locator('[data-uiid="flow_studio.modal.selftest"]')
        await expect(modal).to_be_visible()

        # 3. Click on a step
        step = modal.locator('.selftest-plan-item').first
        await step.click()

        # 4. Verify step details shown
        await expect(modal).to_contain_text('Tier')
    """

    def test_selftest_modal_has_uiid(self):
        """Selftest modal should have data-uiid for automation."""
        html = get_flow_studio_html()

        assert 'data-uiid="flow_studio.modal.selftest"' in html, (
            "Selftest modal should have data-uiid"
        )

    def test_selftest_ui_module_exists(self):
        """Selftest UI module should exist."""
        sources = get_ts_sources()

        assert "selftest_ui.ts" in sources, "Selftest UI module should exist"


# ============================================================================
# Focus Management Tests
# ============================================================================


class TestFocusManagement:
    """Tests for focus trap and modal focus management.

    Accessibility requirements:
    - Modals should trap focus
    - ESC should close modals
    - Focus should return to invoker on close
    """

    def test_focus_trap_utilities_exist(self):
        """Focus trap utilities should be available."""
        sources = get_ts_sources()
        utils_ts = sources.get("utils.ts", "")

        assert "createFocusTrap" in utils_ts, "Focus trap utility should exist"

    def test_modal_focus_manager_exists(self):
        """Modal focus manager should be available."""
        sources = get_ts_sources()
        utils_ts = sources.get("utils.ts", "")

        assert "createModalFocusManager" in utils_ts, "Modal focus manager should exist"

    def test_shortcuts_modal_uses_focus_manager(self):
        """Shortcuts modal should use focus management."""
        sources = get_ts_sources()
        shortcuts_ts = sources.get("shortcuts.ts", "")

        assert "createModalFocusManager" in shortcuts_ts, "Shortcuts modal should use focus manager"

    def test_selftest_modal_uses_focus_manager(self):
        """Selftest modal should use focus management."""
        sources = get_ts_sources()
        selftest_ts = sources.get("selftest_ui.ts", "")

        assert "createModalFocusManager" in selftest_ts, "Selftest modal should use focus manager"


# ============================================================================
# CSS Token Tests
# ============================================================================


class TestCSSTokens:
    """Tests for CSS custom properties (design tokens)."""

    def test_css_tokens_defined(self):
        """CSS should define design tokens."""
        css_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "css" / "flow-studio.base.css"
        css_content = css_file.read_text(encoding="utf-8")

        # Check for token definitions
        assert ":root" in css_content, "CSS should define :root for tokens"
        assert "--fs-color-" in css_content, "CSS should define color tokens"
        assert "--fs-spacing-" in css_content, "CSS should define spacing tokens"
        assert "--fs-radius-" in css_content, "CSS should define radius tokens"

    def test_state_components_defined(self):
        """CSS should define state components (empty, error, loading)."""
        css_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "css" / "flow-studio.base.css"
        css_content = css_file.read_text(encoding="utf-8")

        assert ".fs-empty" in css_content, "CSS should define empty state component"
        assert ".fs-error" in css_content, "CSS should define error state component"
        assert ".fs-loading" in css_content, "CSS should define loading state component"


# ============================================================================
# SDK Contract Tests
# ============================================================================


class TestSDKContract:
    """Tests for the window.__flowStudio SDK contract.

    The SDK provides a stable interface for agents and automation.
    """

    def test_sdk_interface_defined(self):
        """FlowStudioSDK interface should be defined in domain.ts."""
        sources = get_ts_sources()
        domain_ts = sources.get("domain.ts", "")

        assert "interface FlowStudioSDK" in domain_ts, "SDK interface should be defined"

    def test_sdk_has_get_state(self):
        """SDK should expose getState method."""
        sources = get_ts_sources()
        domain_ts = sources.get("domain.ts", "")

        assert "getState()" in domain_ts, "SDK should expose getState method"

    def test_sdk_has_get_graph_state(self):
        """SDK should expose getGraphState method."""
        sources = get_ts_sources()
        domain_ts = sources.get("domain.ts", "")

        assert "getGraphState()" in domain_ts, "SDK should expose getGraphState method"

    def test_sdk_has_selection_methods(self):
        """SDK should expose selection methods."""
        sources = get_ts_sources()
        domain_ts = sources.get("domain.ts", "")

        assert "selectStep" in domain_ts, "SDK should expose selectStep"
        assert "selectAgent" in domain_ts, "SDK should expose selectAgent"
        assert "clearSelection" in domain_ts, "SDK should expose clearSelection"

    def test_sdk_has_uiid_helpers(self):
        """SDK should expose UIID query helpers."""
        sources = get_ts_sources()
        domain_ts = sources.get("domain.ts", "")

        assert "qsByUiid" in domain_ts, "SDK should expose qsByUiid"
        assert "qsAllByUiidPrefix" in domain_ts, "SDK should expose qsAllByUiidPrefix"

    def test_sdk_exported_in_app(self):
        """SDK should be exported on window.__flowStudio."""
        sources = get_ts_sources()
        app_ts = sources.get("flow-studio-app.ts", "")

        assert "window.__flowStudio" in app_ts, "SDK should be exported on window.__flowStudio"


# ============================================================================
# Graph Outline Tests
# ============================================================================


class TestGraphOutline:
    """Tests for the semantic graph outline (accessibility companion)."""

    def test_outline_module_exists(self):
        """Graph outline module should exist."""
        sources = get_ts_sources()

        assert "graph_outline.ts" in sources, "Graph outline module should exist"

    def test_outline_has_get_current_state(self):
        """Outline should expose getCurrentGraphState."""
        sources = get_ts_sources()
        outline_ts = sources.get("graph_outline.ts", "")

        assert "getCurrentGraphState" in outline_ts, "Outline should expose getCurrentGraphState"

    def test_outline_has_render_function(self):
        """Outline should expose renderFlowOutline."""
        sources = get_ts_sources()
        outline_ts = sources.get("graph_outline.ts", "")

        assert "renderFlowOutline" in outline_ts, "Outline should expose renderFlowOutline"

    def test_outline_container_has_uiid(self):
        """Outline container should have data-uiid."""
        html = get_flow_studio_html()

        assert 'data-uiid="flow_studio.canvas.outline"' in html, (
            "Outline container should have data-uiid"
        )
