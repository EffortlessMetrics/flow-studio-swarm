import re
from swarm.tools.flow_studio_ui import get_index_html
from tests.test_flow_studio_ui_ids import extract_uiids_from_html

html = get_index_html()

# Custom logic replicating what extract_uiids_from_html does but debugging
uiids = []
pattern = re.compile(r'data-uiid="([^"]+)"')

# Track whether we're inside a script tag
in_script = False
script_start = re.compile(r"<script\b", re.IGNORECASE)
script_end = re.compile(r"</script>", re.IGNORECASE)

for line_num, line in enumerate(html.split("\n"), start=1):
    # Handle script tag transitions
    if script_start.search(line):
        in_script = True
        print(f"[{line_num}] IN SCRIPT: {line[:50]}...")
    if script_end.search(line):
        in_script = False
        print(f"[{line_num}] OUT SCRIPT: {line[:50]}...")
        continue  # Skip the closing script line

    # Skip lines inside script tags
    if in_script:
        # Check if the missing UIID is here
        if "flow_studio.modal.run_detail.rerun" in line:
            print(f"[{line_num}] FOUND IN SCRIPT: {line.strip()}")
        continue

    for match in pattern.finditer(line):
        value = match.group(1)
        # Skip JavaScript template literals (e.g., ${id} in compiled JS)
        if "${" in value:
            continue
        uiids.append((value, line_num))

print(f"Missing uiid found in extracted? {'flow_studio.modal.run_detail.rerun' in [u[0] for u in uiids]}")
