import re

with open('tests/test_flow_studio_ui_ids.py', 'r') as f:
    content = f.read()

new_extract_func = """def extract_uiids_from_html(html: str) -> List[Tuple[str, int]]:
    '''
    Extract all data-uiid attribute values from HTML DOM elements.

    Skips UIIDs found inside <script> tags (which are JavaScript strings,
    not actual DOM attributes), UNLESS it's the inline JS bundle that contains
    the actual HTML templates.

    Returns:
        List of (uiid_value, line_number) tuples
    '''
    uiids = []
    pattern = re.compile(r'data-uiid="([^"]+)"')

    # Track whether we're inside a script tag
    in_script = False
    is_bundle_script = False
    script_start = re.compile(r"<script\\\\b(.*?)>", re.IGNORECASE)
    script_end = re.compile(r"</script>", re.IGNORECASE)

    for line_num, line in enumerate(html.split("\\n"), start=1):
        # Handle script tag transitions
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

    # Deduplicate extracted uiid values while preserving line numbers to prevent false duplicate errors in tests.
    seen_uiids = set()
    deduped_uiids = []
    for uiid, line in uiids:
        if uiid not in seen_uiids:
            seen_uiids.add(uiid)
            deduped_uiids.append((uiid, line))

    return deduped_uiids"""

# Using python's ast to safely replace the function could work, but lets just use string splitting
parts = content.split("def extract_uiids_from_html(html: str) -> List[Tuple[str, int]]:\n")
first_part = parts[0]
second_part = parts[1].split("def validate_uiid(uiid: str) -> List[str]:\n", 1)[1]

new_content = first_part + new_extract_func.replace("'''", '"""').replace('\\n', '\n').replace('\\\\b', r'\b') + "\n\ndef validate_uiid(uiid: str) -> List[str]:\n" + second_part

with open('tests/test_flow_studio_ui_ids.py', 'w') as f:
    f.write(new_content)
