import re
from tests.test_flow_studio_ui_ids import get_flow_studio_html

html = get_flow_studio_html()

in_script = False
script_start = re.compile(r"<script\b", re.IGNORECASE)
script_end = re.compile(r"</script>", re.IGNORECASE)

pattern = re.compile(r'data-uiid="([^"]+)"')

for line_num, line in enumerate(html.split("\n"), start=1):
    if script_start.search(line):
        in_script = True
        print(f"Line {line_num}: Entered script")
    if script_end.search(line):
        in_script = False
        print(f"Line {line_num}: Exited script")
        continue

    if "rerun" in line:
        print(f"Line {line_num}: (in_script={in_script}) {line.strip()}")
