## 2025-05-19 - Dynamic Component Testing Gap
**Learning:** `test_flow_studio_ui_ids.py` validates static HTML but fails to detect UIIDs in dynamically rendered components (like `run_detail_modal.js`) unless they are explicitly tested via source code inspection (like `TestDynamicUIIDs`). This causes false negatives when components move from static to dynamic rendering.
**Action:** When converting static components to dynamic, move associated UIID tests from `TestFlowStudioUIIDs` to `TestDynamicUIIDs`.
