import re
from tests.test_flow_studio_ui_ids import extract_uiids_from_html

html = """
<div data-uiid="flow_studio.modal.run_detail">
  <button id="run-detail-rerun-btn" data-uiid="flow_studio.modal.run_detail.rerun" class="fs-button-primary" style="flex: 1;">
</div>
"""
uiids = extract_uiids_from_html(html)
print(uiids)
