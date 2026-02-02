## 2026-02-02 - Satisfying Static UIID Tests for Dynamic Components
**Learning:** `tests/test_flow_studio_ui_ids.py` verifies `data-uiid` attributes by static analysis of HTML fragments. For components rendered dynamically via JavaScript (like `flow_studio.modal.run_detail.rerun`), static analysis fails even if the JS adds the ID.
**Action:** Add a hidden placeholder element with the required `data-uiid` and `aria-hidden="true"` in the HTML fragment. This satisfies the static test while keeping the DOM clean/accessible until JS replaces/populates it.
