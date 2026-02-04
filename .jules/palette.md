## 2024-05-22 - Dynamic UI Testing and CSS Logic
**Learning:** Testing dynamic UI elements (created in JS) with static HTML parsers causes false negatives. The project uses `TestDynamicUIIDs` for JS-generated elements. Also, `input:not(:placeholder-shown) ~ .clear-btn` provides efficient JS-free visibility toggling but enforces strict DOM ordering.
**Action:** Register dynamic elements in `TestDynamicUIIDs`, not `TestFlowStudioUIIDs`. Place toggled elements after inputs in DOM when using sibling selectors.

## 2024-05-22 - Guardrail and Mock Reliability
**Learning:** `tests/test_flow_order_guardrail.py` relies on exact line numbers for exceptions, causing brittleness. Similarly, mocking `_run_git` in `ShadowFork` tests is brittle to internal logic changes (like `_resolve_base_ref` calls).
**Action:** Update `ALLOWED_VIOLATIONS` line numbers when editing flagged files. Mock higher-level helper methods (like `_resolve_base_ref`) to stabilize unit tests.
