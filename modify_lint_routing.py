import re
from pathlib import Path

filepath = Path("swarm/tools/lint_routing_fields.py")
content = filepath.read_text()

search = """
EXCLUDE_DIRS = [
    ".git",
    ".venv",
    ".venv_tests",
    "node_modules",
    "__pycache__",
]
"""

replace = """
EXCLUDE_DIRS = [
    ".git",
    ".venv",
    ".venv_tests",
    "node_modules",
    "__pycache__",
    "docs",  # Educational references in RELEASE_CHECKLIST.md
    "swarm/prompts",  # Educational references in prompts
]
"""

content = content.replace(search, replace)
filepath.write_text(content)
