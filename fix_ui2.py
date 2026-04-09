import re
with open("tests/test_flow_studio_ui_ids.py", "r") as f:
    content = f.read()

# Change the script_start regex to NOT match script tags that have data-inline-source="flowstudio-js-bundle"
# or simply remove the script skipping logic since the js bundle is what actually generates the HTML.
# But wait, there might be template variables `${id}` which is why it checks `if "${" in value: continue`.

new_func = """    script_start = re.compile(r"<script(?!.*data-inline-source)\b", re.IGNORECASE)
    script_end = re.compile(r"</script>", re.IGNORECASE)"""

content = re.sub(
    r'    script_start = re.compile\(r"<script\\b", re\.IGNORECASE\)\n    script_end = re.compile\(r"</script>", re\.IGNORECASE\)',
    new_func,
    content
)

with open("tests/test_flow_studio_ui_ids.py", "w") as f:
    f.write(content)
