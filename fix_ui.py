import re

with open("tests/test_flow_studio_ui_ids.py", "r") as f:
    content = f.read()

# Make sure it only skips ACTUAL <script> tags, not <script type="application/json"> which is just data
# The pattern should be `r"<script(?![^>]*type=\"application/json\")\b"`
# But the `<script type="application/json" data-inline-source="flowstudio-js-bundle">` contains the actual code as a string! Wait, no, the builder replaces `<script type="module" src="js/main.js"></script>` with `<script type="application/json" data-inline-source="flowstudio-js-bundle">` and puts the raw JS inside. But wait, `data-uiid="flow_studio.modal.run_detail.rerun"` is inside the string. Wait, if it's inside JS, why is the test expecting to find it there?
# Ah! In the compiled JS bundle, the UI string template contains `data-uiid="flow_studio.modal.run_detail.rerun"`.
# The test extracts UIIDs from HTML, but it *explicitly skips* script tags!
# In `swarm/tools/flow_studio_ui/src/run_detail_modal.ts` it's generated dynamically via JS string literal.
# Because the `index.html` is bundled, the JS is inside `<script>`.
# Why did `test_flow_studio_ui_ids.py` pass locally/earlier but fail now?
# Wait! Previously it was an actual DOM element in index.html, but someone moved it to JS.
# Oh, we see index.html has:
# 322:<div id="run-detail-modal" class="selftest-modal" role="dialog" aria-modal="true" aria-labelledby="run-detail-modal-title" data-uiid="flow_studio.modal.run_detail">
# 323:  <div class="selftest-step-content" data-uiid="flow_studio.modal.run_detail.body">
# 324:    <button class="selftest-modal-close" id="run-detail-close" aria-label="Close run detail modal" data-uiid="flow_studio.modal.run_detail.close">×</button>
# So it has close button, but NO RERUN BUTTON!
# The rerun button is created in TS/JS dynamically.
# Therefore, it is inside the script. The test `test_run_detail_rerun_button_has_uiid` says "html = get_flow_studio_html()".
# Then `extract_uiids_from_html` skips script tags, so it doesn't see it.
# We should probably allow the JS strings to be parsed for UIIDs if they are inside `<script type="application/json" data-inline-source="flowstudio-js-bundle">` or just don't skip script tags at all? The test comment says:
# "Skips UIIDs found inside <script> tags (which are JavaScript strings, not actual DOM attributes)."
# But what if the JS string generates DOM elements? The test for it expects it!
# Wait! In the past, the test `test_run_detail_modal_elements_have_uiids` expected it.
