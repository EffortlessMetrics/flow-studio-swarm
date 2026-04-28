from swarm.tools.flow_studio_ui import get_index_html
from tests.test_flow_studio_ui_ids import extract_uiids_from_html

html = get_index_html()
uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}
print("flow_studio.modal.run_detail.rerun" in uiids)
