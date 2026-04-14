from tests.test_flow_studio_ui_ids import get_flow_studio_html, extract_uiids_from_html

html = get_flow_studio_html()
uiids = extract_uiids_from_html(html)
print(f"Total UIIDs: {len(uiids)}")
rerun_uiid = [u for u in uiids if "rerun" in u[0]]
print(f"Rerun UIIDs: {rerun_uiid}")
