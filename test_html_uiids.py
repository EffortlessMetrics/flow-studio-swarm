import re
def extract_uiids_from_html(html: str):
    uiids = []
    pattern = re.compile(r'data-uiid="([^"]+)"')

    # Track whether we're inside a script tag
    in_script = False
    script_start = re.compile(r"<script\b", re.IGNORECASE)
    script_end = re.compile(r"</script>", re.IGNORECASE)

    for line_num, line in enumerate(html.split("\n"), start=1):
        if 'application/json' in line and 'data-inline-source="flowstudio-js-bundle"' in line:
            # esbuild inline template
            in_script = False

        if script_start.search(line):
            if 'application/json' in line and 'data-inline-source="flowstudio-js-bundle"' in line:
                in_script = False
            else:
                in_script = True
        if script_end.search(line):
            in_script = False
            continue  # Skip the closing script line

        # Skip lines inside script tags
        if in_script:
            continue

        for match in pattern.finditer(line):
            value = match.group(1)
            # Skip JavaScript template literals (e.g., ${id} in compiled JS)
            if "${" in value:
                continue
            uiids.append((value, line_num))

    return uiids

with open("swarm/tools/flow_studio_ui/index.html") as f:
    uiids = extract_uiids_from_html(f.read())
    print("flow_studio.modal.run_detail.rerun" in [u for u, _ in uiids])
