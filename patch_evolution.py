import re

filepath = "swarm/api/routes/evolution.py"
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
    content = content.replace('tags=["evolution"])\n', 'tags=["evolution"])\n' + helper)

endpoints_evo = {
    "get_run_evolution_patches": [("run_id", "run_id")],
    "get_evolution_patch_details": [("run_id", "run_id"), ("patch_id", "patch_id")],
    "validate_evolution_patch_endpoint": [("run_id", "run_id"), ("patch_id", "patch_id")],
    "reject_evolution_patch_endpoint": [("run_id", "run_id"), ("patch_id", "patch_id")],
}

for ep, rules in endpoints_evo.items():
    # Allow matching def with params over multiple lines and docstrings.
    pattern = re.compile(r'(async def ' + ep + r'\([^)]*\):(?:[\s]*"""[\s\S]*?""")?)', re.MULTILINE)
    match = pattern.search(content)
    if match:
        injection = ""
        for r in rules:
            injection += f"\n    _validate_path({r[0]}, \"{r[1]}\")"

        content = content[:match.end()] + injection + content[match.end():]

# Special case for apply_evolution_patch_endpoint
pattern = re.compile(r'(async def apply_evolution_patch_endpoint\([^)]*\):(?:[\s]*"""[\s\S]*?""")?)', re.MULTILINE)
match = pattern.search(content)
if match:
    injection = """
    if ":" in request.patch_id:
        r_id, p_id = request.patch_id.split(":", 1)
        _validate_path(r_id, "run_id")
        _validate_path(p_id, "patch_id")
    else:
        _validate_path(request.patch_id, "patch_id")
"""
    content = content[:match.end()] + injection + content[match.end():]


with open(filepath, 'w') as f:
    f.write(content)
