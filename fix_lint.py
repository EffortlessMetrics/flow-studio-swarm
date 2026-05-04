import re

with open("swarm/tools/lint_routing_fields.py", "r") as f:
    content = f.read()

# Add docs/RELEASE_CHECKLIST.md and swarm/prompts/agentic_steps/self-reviewer.md to SKIP_PATTERNS
content = content.replace(
    '    "**/run_state.json",  # Stepwise state machine uses advance/terminate/error/loop\n]',
    '    "**/run_state.json",  # Stepwise state machine uses advance/terminate/error/loop\n'
    '    "**/docs/RELEASE_CHECKLIST.md",  # Deprecation documentation\n'
    '    "**/swarm/prompts/agentic_steps/self-reviewer.md",  # Deprecation documentation\n]'
)

with open("swarm/tools/lint_routing_fields.py", "w") as f:
    f.write(content)
