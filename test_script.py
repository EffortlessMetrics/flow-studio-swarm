import re

html = """
<script type="application/json" data-inline-source="flowstudio-js-bundle">
<button id="run-detail-rerun-btn" data-uiid="flow_studio.modal.run_detail.rerun" class="fs-button-primary" style="flex: 1;">
</script>
"""

uiids = []
pattern = re.compile(r'data-uiid="([^"]+)"')

# Track whether we're inside a script tag
in_script = False
is_bundle_script = False
script_start = re.compile(r"<script\b(.*?)>", re.IGNORECASE)
script_end = re.compile(r"</script>", re.IGNORECASE)

for line_num, line in enumerate(html.split("\n"), start=1):
    print(f"line: {line}, in_script: {in_script}, is_bundle_script: {is_bundle_script}")
    match = script_start.search(line)
    if match:
        in_script = True
        if "flowstudio-js-bundle" in match.group(1):
            is_bundle_script = True

    if script_end.search(line):
        in_script = False
        is_bundle_script = False
        continue  # Skip the closing script line

    # Skip lines inside script tags, UNLESS it's the bundle script
    if in_script and not is_bundle_script:
        continue

    for match in pattern.finditer(line):
        value = match.group(1)
        # Skip JavaScript template literals (e.g., ${id} in compiled JS)
        if "${" in value:
            continue
        uiids.append((value, line_num))

print(uiids)
