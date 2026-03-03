import swarm.tools.flow_studio_ui as ui
import re

html = ui.get_index_html()
in_script = False
script_start = re.compile(r'<script\b', re.IGNORECASE)
script_end = re.compile(r'</script>', re.IGNORECASE)
uiids = []
pattern = re.compile(r'data-uiid="([^"]+)"')

for line_num, line in enumerate(html.split('\n'), start=1):
    if script_start.search(line):
        in_script = True
    if script_end.search(line):
        in_script = False
        continue

    if in_script:
        continue

    for match in pattern.finditer(line):
        uiids.append(match.group(1))

print('flow_studio.modal.run_detail.rerun' in uiids)
