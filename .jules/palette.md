## 2024-05-22 - Static Analysis of UIIDs vs Dynamic Rendering
**Learning:** `tests/test_flow_studio_ui_ids.py` validates `data-uiid` attributes by parsing `index.html` statically. Elements rendered dynamically via JavaScript (e.g., inside template strings or `document.createElement`) are invisible to this tool, leading to false positives if listed in static expectations.
**Action:** When adding UIIDs to dynamic components, exclude them from static `TestFlowStudioUIIDs` expectations and verify them via `TestDynamicUIIDs` (checking JS source) or integration tests instead.
