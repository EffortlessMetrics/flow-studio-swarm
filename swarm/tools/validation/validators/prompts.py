# swarm/tools/validation/validators/prompts.py
"""
FR-006: Agent Prompt Section Validation

Validates that agent prompt bodies include required sections.

LEGACY: This check is skipped if .claude/agents/ directory does not exist.
The new architecture uses swarm/config/agents/ for agent configuration instead.

Checks for presence of these required headings after frontmatter:
- ## Inputs (or ## Input)
- ## Outputs (or ## Output)
- ## Behavior
"""

import re
from typing import Any, Dict, List

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import ROOT, AGENTS_DIR
from swarm.tools.validation.constants import BUILT_IN_AGENTS


def validate_prompt_sections(registry: Dict[str, Dict[str, Any]], strict_mode: bool = False) -> ValidationResult:
    """
    Validate that agent prompt bodies include required sections.

    LEGACY: This check is skipped if .claude/agents/ directory does not exist.
    The new architecture uses swarm/config/agents/ for agent configuration instead.

    FR-006: Agent Prompt Sections
    Checks for presence of these required headings after frontmatter:
    - ## Inputs (or ## Input)
    - ## Outputs (or ## Output)
    - ## Behavior

    Args:
        registry: Agent registry from AGENTS.md
        strict_mode: If True, missing sections are errors; if False, warnings

    Returns:
        ValidationResult with errors or warnings for missing sections
    """
    result = ValidationResult()

    # LEGACY: Skip prompt sections check if .claude/agents/ doesn't exist
    # The new architecture uses swarm/config/agents/ instead
    if not AGENTS_DIR.is_dir():
        return result

    # Patterns to match required sections (case-insensitive)
    input_pattern = re.compile(r"^##\s+Inputs?\s*$", re.IGNORECASE | re.MULTILINE)
    output_pattern = re.compile(r"^##\s+Outputs?\s*$", re.IGNORECASE | re.MULTILINE)
    behavior_pattern = re.compile(r"^##\s+Behavior\s*$", re.IGNORECASE | re.MULTILINE)

    for path in sorted(AGENTS_DIR.glob("*.md")):
        if path.is_symlink():
            # Skip symlinks: validation only applies to real files
            continue

        filename_key = path.stem
        rel_path = path.relative_to(ROOT)

        # Skip built-in agents
        if filename_key in BUILT_IN_AGENTS:
            continue

        # Only validate project/user agents in registry
        if filename_key not in registry:
            continue

        agent_meta = registry[filename_key]
        if agent_meta.get("source") != "project/user":
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            # Skip files that can't be read (already reported elsewhere)
            continue

        # Extract the body after frontmatter
        # Frontmatter is between first --- and second ---
        if content.startswith("---"):
            # Find the closing ---
            end_idx = content.find("---", 3)
            if end_idx != -1:
                body = content[end_idx + 3:].strip()
            else:
                body = ""
        else:
            body = content

        missing_sections: List[str] = []

        if not input_pattern.search(body):
            missing_sections.append("## Inputs")

        if not output_pattern.search(body):
            missing_sections.append("## Outputs")

        if not behavior_pattern.search(body):
            missing_sections.append("## Behavior")

        if missing_sections:
            location = str(rel_path)
            problem = f"missing required prompt sections: {', '.join(missing_sections)}"
            fix_action = f"Add the following sections to agent prompt: {', '.join(missing_sections)}"

            if strict_mode:
                result.add_error(
                    "PROMPT",
                    location,
                    problem,
                    fix_action,
                    file_path=str(path)
                )
            else:
                result.add_warning(
                    "PROMPT",
                    location,
                    problem,
                    fix_action,
                    file_path=str(path)
                )

    return result
