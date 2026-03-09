import re

filepath = "swarm/api/routes/wisdom.py"
with open(filepath, 'r') as f:
    content = f.read()

import_stmt = "from swarm.runtime.safe_paths import validate_path_component\n"
if "from swarm.runtime.safe_paths" not in content:
    content = content.replace("from fastapi import", f"{import_stmt}from fastapi import", 1)

helper = """

def _validate_path(val: str, name: str) -> None:
    if val is not None:
        try:
            validate_path_component(val, name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail={"error": "invalid_path", "message": str(e), "details": {name: val}})
"""
if "_validate_path" not in content:
    content = content.replace('tags=["wisdom"])\n', 'tags=["wisdom"])\n' + helper)

endpoints_wis = {
    "get_wisdom_artifacts": [("run_id", "run_id")],
    "get_wisdom_content": [("run_id", "run_id"), ("artifact_name", "artifact_name")],
    "apply_wisdom_patch": [("run_id", "run_id"), ("request.artifact_name", "artifact_name")],
    "reject_wisdom_patch": [("run_id", "run_id"), ("request.artifact_name", "artifact_name")],
    "apply_wisdom_patches": [("run_id", "run_id")],
}

for ep, rules in endpoints_wis.items():
    pattern = re.compile(r'(async def ' + ep + r'\([^)]*\):(?:[\s]*"""[\s\S]*?""")?)', re.MULTILINE)
    match = pattern.search(content)
    if match:
        injection = ""
        for r in rules:
            injection += f"\n    _validate_path({r[0]}, \"{r[1]}\")"

        content = content[:match.end()] + injection + content[match.end():]

with open(filepath, 'w') as f:
    f.write(content)
