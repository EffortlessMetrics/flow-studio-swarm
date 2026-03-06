1. **Fix `test_flow_order_guardrail.py` (Stale Entries)**
   - The guardrail test fails because `swarm/tools/validation/reporting/json_output.py:126` is in the `ALLOWED_VIOLATIONS` dictionary but the line no longer contains the hardcoded flow list.
   - However, `swarm/tools/validation/reporting/json_output.py:139` has hardcoded flow lists `["signal", "plan", "build"]` and `["signal", "plan", "build", "review", "gate", "deploy", "wisdom"]` which failed the test.
   - Action: Update `ALLOWED_VIOLATIONS` in `tests/test_flow_order_guardrail.py` to change line `126` to `139` for `swarm/tools/validation/reporting/json_output.py`.
2. **Fix `test_flow_studio_ui_ids.py` (Missing UIID)**
   - The test expects a run detail rerun button to have `data-uiid="flow_studio.modal.run_detail.rerun"`.
   - Action: Add `data-uiid="flow_studio.modal.run_detail.rerun"` to the rerun button in `swarm/tools/flow_studio_ui/fragments/60-modals.html`.
3. **Rebuild the frontend**
   - Run `make gen-index-html` to propagate changes to `index.html`.
4. **Fix `test_shadow_fork.py` (Test logic bugs)**
   - `test_create_fails_if_base_branch_missing` throws `StopIteration`. This happens because the mock for `_run_git` is likely an array and it ran out of elements when fallbacks logic was triggered. Need to replace array with a `side_effect` callable.
   - `test_create_warns_on_uncommitted_changes` has empty caplog. Needs setting `caplog.set_level(logging.WARNING, logger="swarm.runtime.shadow_fork")`.
5. **Verify changes**
   - Run tests to make sure they pass: `uv run pytest tests/test_flow_order_guardrail.py tests/test_flow_studio_ui_ids.py tests/test_shadow_fork.py`.
6. **Pre-commit steps**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
