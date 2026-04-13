with open('swarm/tools/flow_studio_ui/index.html') as f:
    html = f.read()

import re
uiids = []
pattern = re.compile(r'data-uiid="([^"]+)"')
in_script = False
script_start = re.compile(r'<script\b', re.IGNORECASE)
script_end = re.compile(r'</script>', re.IGNORECASE)

for line_num, line in enumerate(html.split('\n'), start=1):
    if script_start.search(line):
        in_script = True

    if script_end.search(line):
        in_script = False
        continue

    if in_script:
        if 'flow_studio.modal.run_detail.rerun' in line:
            print(f'Found inside script block on line {line_num}: {line}')
        continue

    for match in pattern.finditer(line):
        value = match.group(1)
        if '${' in value:
            continue
        uiids.append((value, line_num))

print('flow_studio.modal.run_detail.rerun' in [u[0] for u in uiids])
