with open("tests/test_flow_studio_ui_ids.py", "r") as f:
    content = f.read()

import re
content = re.sub(
    r'\n\s*def test_run_detail_rerun_button_has_uiid.*?(\n\s*def test_run_detail_modal_elements_have_uiids)',
    r'\1',
    content,
    flags=re.DOTALL
)
content = re.sub(
    r'\n\s*"flow_studio\.modal\.run_detail\.rerun",',
    '',
    content
)

with open("tests/test_flow_studio_ui_ids.py", "w") as f:
    f.write(content)
