#!/usr/bin/env python3
"""
Golden path test for Flow Studio SDK + data-uiid selectors.

This test validates that the public automation contract is usable:
1. window.__flowStudio SDK is properly exported
2. data-uiid selectors identify all key elements
3. The SDK methods exist for common operations

For actual browser testing with Playwright, the pattern is:

```python
@pytest.mark.asyncio
async def test_sdk_can_navigate_and_select_step(page):
    await page.goto('http://localhost:5000')
    await page.wait_for_selector('html[data-ui-ready="ready"]')

    # Use the SDK from inside the browser
    await page.evaluate('''
    async () => {
      const sdk = window.__flowStudio;
      if (!sdk) throw new Error("Flow Studio SDK not available");

      await sdk.setActiveFlow("build");
      await sdk.selectStep("build", "1");
    }
    ''')

    # Assert the inspector reflects the selected step
    details = await page.inner_text('[data-uiid="flow_studio.inspector"]')
    assert "Step:" in details.lower() or "build" in details.lower()
```

This module validates the contract exists without requiring a browser.
"""

import re
import sys
from pathlib import Path

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


def get_ts_source(name: str) -> str:
    """Load a specific TypeScript source file."""
    ts_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "src" / name
    if ts_file.exists():
        return ts_file.read_text(encoding="utf-8")
    return ""


def get_all_ts_sources() -> str:
    """Concatenate all TypeScript sources for searching."""
    ts_dir = repo_root / "swarm" / "tools" / "flow_studio_ui" / "src"
    sources = []
    for ts_file in ts_dir.glob("*.ts"):
        sources.append(ts_file.read_text(encoding="utf-8"))
    return "\n".join(sources)


# ============================================================================
# SDK Export Test
# ============================================================================


class TestSDKExport:
    """Tests that the Flow Studio SDK is properly exported."""

    def test_sdk_exported_on_window(self):
        """window.__flowStudio should be set during initialization."""
        app_ts = get_ts_source("flow-studio-app.ts")

        assert "window.__flowStudio" in app_ts, "SDK should be exported on window.__flowStudio"

    def test_sdk_has_typed_interface(self):
        """FlowStudioSDK interface should be defined in domain.ts."""
        domain_ts = get_ts_source("domain.ts")

        assert "interface FlowStudioSDK" in domain_ts, "SDK should have a typed interface"

    def test_sdk_interface_includes_required_methods(self):
        """SDK interface should include the required methods for automation."""
        domain_ts = get_ts_source("domain.ts")

        required_methods = [
            "getState",  # Get current UI state
            "setActiveFlow",  # Navigate to a flow
            "selectStep",  # Select a step in the current flow
            "selectAgent",  # Select an agent
            "clearSelection",  # Clear current selection
        ]

        for method in required_methods:
            assert method in domain_ts, f"SDK should expose '{method}' method"


# ============================================================================
# SDK State Contract Test
# ============================================================================


class TestSDKStateContract:
    """Tests for the SDK getState() contract."""

    def test_state_includes_current_flow(self):
        """SDK state should include current flow key."""
        domain_ts = get_ts_source("domain.ts")

        assert "currentFlowKey" in domain_ts, "SDK state should include currentFlowKey"

    def test_state_includes_selection(self):
        """SDK state should include selection information."""
        domain_ts = get_ts_source("domain.ts")

        assert "selectedNodeId" in domain_ts, "SDK state should include selectedNodeId"
        assert "selectedNodeType" in domain_ts, "SDK state should include selectedNodeType"

    def test_state_includes_run_info(self):
        """SDK state should include run information."""
        domain_ts = get_ts_source("domain.ts")

        assert "currentRunId" in domain_ts, (
            "SDK state should include 'currentRunId' in FlowStudioSDK.getState()"
        )


# ============================================================================
# UIID Selector Contract Test
# ============================================================================


class TestUIIDSelectors:
    """Tests that key elements have data-uiid selectors."""

    def test_inspector_has_uiid(self):
        """Inspector panel should have data-uiid for automation.

        Playwright selector: [data-uiid="flow_studio.inspector"]
        """
        html = get_flow_studio_html()
        assert 'data-uiid="flow_studio.inspector"' in html

    def test_flow_list_has_uiid(self):
        """Flow list should have data-uiid for automation.

        Playwright selector: [data-uiid="flow_studio.sidebar.flow_list"]
        """
        html = get_flow_studio_html()
        assert 'data-uiid="flow_studio.sidebar.flow_list"' in html

    def test_search_input_has_uiid(self):
        """Search input should have data-uiid for automation.

        Playwright selector: [data-uiid="flow_studio.header.search.input"]
        """
        html = get_flow_studio_html()
        assert 'data-uiid="flow_studio.header.search.input"' in html

    def test_canvas_outline_has_uiid(self):
        """Canvas outline should have data-uiid for automation.

        Playwright selector: [data-uiid="flow_studio.canvas.outline"]
        """
        html = get_flow_studio_html()
        assert 'data-uiid="flow_studio.canvas.outline"' in html


# ============================================================================
# SDK Helper Methods Test
# ============================================================================


class TestSDKHelperMethods:
    """Tests that SDK helper methods exist for automation."""

    def test_sdk_has_uiid_query_helper(self):
        """SDK should expose helper to query by data-uiid.

        Usage: window.__flowStudio.qsByUiid('flow_studio.inspector')
        """
        domain_ts = get_ts_source("domain.ts")

        assert "qsByUiid" in domain_ts, "SDK should expose qsByUiid helper"

    def test_sdk_has_uiid_prefix_query_helper(self):
        """SDK should expose helper to query by data-uiid prefix.

        Usage: window.__flowStudio.qsAllByUiidPrefix('flow_studio.canvas.outline.step:')
        """
        domain_ts = get_ts_source("domain.ts")

        assert "qsAllByUiidPrefix" in domain_ts, "SDK should expose qsAllByUiidPrefix helper"


# ============================================================================
# UI Ready Handshake Test
# ============================================================================


class TestUIReadyHandshake:
    """Tests for the UI readiness handshake."""

    def test_ui_ready_attribute_on_html(self):
        """HTML element should have data-ui-ready attribute.

        Playwright wait: await page.wait_for_selector('html[data-ui-ready="ready"]')
        """
        html = get_flow_studio_html()
        assert "data-ui-ready=" in html

    def test_ready_state_is_set_on_success(self):
        """UI should set data-ui-ready="ready" when initialization succeeds."""
        all_ts = get_all_ts_sources()

        # Check that ready state helpers exist
        assert "function markUiLoading" in all_ts, "UI should define a markUiLoading helper"
        assert "function markUiReady" in all_ts, "UI should define a markUiReady helper"
        assert "function markUiError" in all_ts, "UI should define a markUiError helper"


# ============================================================================
# Golden Path Integration Test
# ============================================================================


class TestGoldenPathContract:
    """Integration test validating the complete automation contract.

    This test verifies that all pieces of the golden path exist:
    1. SDK is exported on window.__flowStudio
    2. SDK has required navigation methods
    3. data-uiid selectors exist on key elements
    4. UI ready handshake is in place
    """

    def test_complete_automation_contract(self):
        """Validate the complete automation contract exists.

        This test proves that an automation script like:

        ```javascript
        // 1. Wait for UI to be ready
        await page.wait_for_selector('html[data-ui-ready="ready"]');

        // 2. Use SDK to navigate
        await page.evaluate(async () => {
          await window.__flowStudio.setActiveFlow('build');
          await window.__flowStudio.selectStep('build', '1');
        });

        // 3. Use data-uiid to verify state
        const inspector = document.querySelector('[data-uiid="flow_studio.inspector"]');
        ```

        has all the required pieces in place.
        """
        html = get_flow_studio_html()
        domain_ts = get_ts_source("domain.ts")
        app_ts = get_ts_source("flow-studio-app.ts")

        # 1. UI ready handshake
        assert "data-ui-ready=" in html, "UI ready attribute missing"

        # 2. SDK export
        assert "window.__flowStudio" in app_ts, "SDK not exported"

        # 3. Navigation methods
        assert "setActiveFlow" in domain_ts, "setActiveFlow method missing"
        assert "selectStep" in domain_ts, "selectStep method missing"

        # 4. Key UIID selectors
        assert 'data-uiid="flow_studio.inspector"' in html, "Inspector UIID missing"
        assert 'data-uiid="flow_studio.canvas.outline"' in html, "Outline UIID missing"

    def test_step_selection_updates_url(self):
        """Step selection should update URL for shareability."""
        selection_ts = get_ts_source("selection.ts")

        assert "updateURL" in selection_ts, "Step selection should update URL"

    def test_selection_module_is_unified(self):
        """There should be a unified selection module.

        This ensures all selection (graph click, outline click, SDK call)
        goes through a single code path.
        """
        selection_ts = get_ts_source("selection.ts")

        assert "export" in selection_ts, "Selection module should export functions"
        assert "selectNode" in selection_ts, "Selection module should have selectNode"


# ============================================================================
# Playwright Script Documentation
# ============================================================================


class TestPlaywrightScriptDocumentation:
    """Tests that document the expected Playwright usage patterns.

    These tests serve as executable documentation. The test names and
    docstrings describe exactly how to use the SDK and selectors.
    """

    def test_pattern_navigate_to_flow(self):
        """Pattern: Navigate to a specific flow.

        ```javascript
        await page.evaluate(async () => {
          await window.__flowStudio.setActiveFlow('build');
        });

        // Verify
        const state = await page.evaluate(() => window.__flowStudio.getState());
        expect(state.currentFlowKey).toBe('build');
        ```
        """
        domain_ts = get_ts_source("domain.ts")
        assert "setActiveFlow" in domain_ts
        assert "currentFlowKey" in domain_ts

    def test_pattern_select_step(self):
        """Pattern: Select a step and verify inspector.

        ```javascript
        await page.evaluate(async () => {
          await window.__flowStudio.selectStep('build', '1');
        });

        // Verify via inspector
        const details = await page.innerText('[data-uiid="flow_studio.inspector"]');
        expect(details).toContain('Step');
        ```
        """
        domain_ts = get_ts_source("domain.ts")
        html = get_flow_studio_html()

        assert "selectStep" in domain_ts
        assert 'data-uiid="flow_studio.inspector"' in html

    def test_pattern_query_by_uiid(self):
        """Pattern: Query elements using data-uiid.

        ```javascript
        // Single element
        const inspector = await page.locator('[data-uiid="flow_studio.inspector"]');

        // Multiple elements with prefix
        const steps = await page.locator('[data-uiid^="flow_studio.canvas.outline.step:"]').all();
        ```
        """
        html = get_flow_studio_html()

        # Just verify pattern works with some UIIDs
        assert re.search(r'data-uiid="flow_studio\.[^"]+"', html)

    def test_pattern_wait_for_ready(self):
        """Pattern: Wait for UI initialization.

        ```javascript
        // Wait for successful init
        await page.wait_for_selector('html[data-ui-ready="ready"]');

        // Or check for error state
        const state = await page.getAttribute('html', 'data-ui-ready');
        if (state === 'error') {
          throw new Error('UI initialization failed');
        }
        ```
        """
        html = get_flow_studio_html()
        assert "data-ui-ready=" in html
