from tests.test_flow_studio_ui_ids import extract_uiids_from_html, get_flow_studio_html
html = get_flow_studio_html()
uiids = {uiid for uiid, _ in extract_uiids_from_html(html)}
print("flow_studio.modal.run_detail.rerun" in uiids)
print("Is rerun in uiids list?", "flow_studio.modal.run_detail.rerun" in uiids)

script_lines = []
in_script = False
import re
script_start = re.compile(r"<script\b", re.IGNORECASE)
script_end = re.compile(r"</script>", re.IGNORECASE)

for i, line in enumerate(html.split('\n')):
    if script_start.search(line): in_script = True
    if "flow_studio.modal.run_detail.rerun" in line:
        print(f"Found on line {i+1}, in_script={in_script}")
    if script_end.search(line): in_script = False
