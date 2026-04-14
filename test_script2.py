import re
from tests.test_flow_studio_ui_ids import get_flow_studio_html

html = get_flow_studio_html()

pattern = re.compile(r'data-uiid="([^"]+)"')
matches = pattern.finditer(html)
for match in matches:
    if "rerun" in match.group(1):
        print(f"Found rerun: {match.group(1)}")
