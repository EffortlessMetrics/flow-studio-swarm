## 2024-05-24 - Dynamic UI Testing Patterns
**Learning:** Dynamic UI elements (like buttons added via JS) require static HTML placeholders in fragments to satisfy `tests/test_flow_studio_ui_ids.py` and `tests/test_flow_studio_a11y.py`. These placeholders should be hidden but must include required `data-uiid` and accessibility attributes (like `aria-label`) because the tests parse the static HTML files directly.
**Action:** When adding dynamic components, always add a corresponding hidden placeholder in the HTML fragment with full accessibility attributes.
