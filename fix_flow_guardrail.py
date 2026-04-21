with open("swarm/tools/validation/reporting/json_output.py", "r") as f:
    content = f.read()
content = content.replace(
    'flow_keys = ["signal", "plan", "build", "review", "gate", "deploy", "wisdom"]',
    'from swarm.config.flow_registry import get_flow_order\n        flow_keys = get_flow_order()'
)
with open("swarm/tools/validation/reporting/json_output.py", "w") as f:
    f.write(content)

with open("tests/test_flow_order_guardrail.py", "r") as f:
    content = f.read()

import re
content = re.sub(
    r'\s*"swarm/tools/validation/reporting/json_output\.py": \{\n\s*126: "Fallback constant when flow_registry import fails",\n\s*\},',
    "",
    content
)
with open("tests/test_flow_order_guardrail.py", "w") as f:
    f.write(content)
