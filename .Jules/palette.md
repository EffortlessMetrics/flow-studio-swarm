## 2025-05-15 - Testing Dynamic UI Elements
**Learning:** Flow Studio integration tests verify the presence of UI elements by parsing static HTML fragments, even if those elements are dynamically rendered by JS.
**Action:** When adding or fixing dynamic UI elements (like the 'Re-run' button), always ensure a static placeholder with the corresponding `data-uiid` is present in the HTML fragment (even if hidden), so static analysis tests like `test_flow_studio_ui_ids.py` can validate them.
