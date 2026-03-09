import re

filepath = "swarm/api/routes/evolution.py"
with open(filepath, 'r') as f:
    content = f.read()

endpoints_evo = {
    "get_evolution_patch_details": [("run_id", "run_id"), ("patch_id", "patch_id")],
}

for ep, rules in endpoints_evo.items():
    pattern = re.compile(r'(async def ' + ep + r'\([^)]*\):(?:[\s]*"""[\s\S]*?""")?)', re.MULTILINE)
    match = pattern.search(content)
    if match:
        injection = ""
        for r in rules:
            injection += f"\n    _validate_path({r[0]}, \"{r[1]}\")"

        content = content[:match.end()] + injection + content[match.end():]

with open(filepath, 'w') as f:
    f.write(content)
