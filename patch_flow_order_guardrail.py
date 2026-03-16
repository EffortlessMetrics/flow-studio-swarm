import re

with open('tests/test_flow_order_guardrail.py', 'r') as f:
    content = f.read()

# Replace the stale entry in ALLOWED_VIOLATIONS
content = content.replace(
    '    "swarm/tools/validation/reporting/json_output.py": {\n        126: "Fallback constant when flow_registry import fails",\n    },',
    '    "swarm/tools/validation/reporting/json_output.py": {\n        139: "Fallback constant when flow_registry import fails",\n    },'
)

with open('tests/test_flow_order_guardrail.py', 'w') as f:
    f.write(content)
