import swarm.tools.flow_studio_ui as ui
import re

html = ui.get_index_html()
in_script = False
script_start = re.compile(r'<script\b', re.IGNORECASE)
script_end = re.compile(r'</script>', re.IGNORECASE)

for line_num, line in enumerate(html.split('\n'), start=1):
    if script_start.search(line):
        in_script = True
        print(f"Line {line_num}: script start -> {line[:50]}")
    if script_end.search(line):
        in_script = False
        print(f"Line {line_num}: script end -> {line[:50]}")

    if line_num == 12043:
        print(f"Line {line_num}: in_script is {in_script}")
