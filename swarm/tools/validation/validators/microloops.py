# swarm/tools/validation/validators/microloops.py
"""
Microloop Phrase Validation

Validates that deprecated microloop phrases are not used.

Banned phrases (old iteration logic):
- "restat"
- "until the reviewer is satisfied or can only restate concerns"
- "can only restate concerns"
- "restating same concerns"

Allowed alternatives:
- "can_further_iteration_help: yes"
- "can_further_iteration_help: no"
- Status-based logic (VERIFIED/UNVERIFIED + iteration guidance)

Checks:
- Flow specs (.claude/commands/*.md, swarm/flows/*.md)
- Main documentation (CLAUDE.md)
- Agent definitions (.claude/agents/*.md)
"""

import re
from pathlib import Path

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import ROOT, FLOW_SPECS_DIR, AGENTS_DIR


def validate_microloop_phrases() -> ValidationResult:
    """
    Validate that deprecated microloop phrases are not used.

    Banned phrases (old iteration logic):
    - "restat"
    - "until the reviewer is satisfied or can only restate concerns"
    - "can only restate concerns"
    - "restating same concerns"

    Allowed alternatives:
    - "can_further_iteration_help: yes"
    - "can_further_iteration_help: no"
    - Status-based logic (VERIFIED/UNVERIFIED + iteration guidance)

    Checks:
    - Flow specs (.claude/commands/*.md, swarm/flows/*.md)
    - Main documentation (CLAUDE.md)
    - Agent definitions (.claude/agents/*.md)
    """
    result = ValidationResult()

    # Banned phrases list
    banned_phrases = [
        r"restat",  # Catches "restate", "restating", etc.
        r"until the reviewer is satisfied or can only restate concerns",
        r"can only restate concerns",
        r"restating same concerns",
        r"until the reviewer is satisfied\s+or",  # Partial old pattern
    ]

    # Directories to check
    check_dirs = [
        (ROOT / ".claude" / "commands", "Commands"),
        (ROOT / "swarm" / "flows", "Flow Specs"),
        (ROOT / ".claude" / "agents", "Agent Definitions"),
    ]

    # Check root-level CLAUDE.md
    check_files = [
        (ROOT / "CLAUDE.md", "CLAUDE.md"),
    ]

    # Helper: check file for banned phrases
    def check_file_for_banned_phrases(file_path: Path, _display_name: str) -> None:
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            for i, line in enumerate(lines, start=1):
                # Skip comments and code blocks that might be examples
                if line.strip().startswith("#"):
                    continue

                for banned_phrase in banned_phrases:
                    if re.search(banned_phrase, line, re.IGNORECASE):
                        rel_path = file_path.relative_to(ROOT)
                        result.add_error(
                            "MICROLOOP",
                            f"{rel_path}:line {i}",
                            f"uses banned microloop phrase '{banned_phrase}' (old iteration logic)",
                            "Replace with explicit 'can_further_iteration_help: yes/no' or Status-based exit logic",
                            line_number=i,
                            file_path=str(file_path)
                        )
        except (OSError, UnicodeDecodeError):
            pass  # Skip files that can't be read

    # Check specified files
    for file_path, display_name in check_files:
        if file_path.is_file():
            check_file_for_banned_phrases(file_path, display_name)

    # Check directories
    for dir_path, display_name in check_dirs:
        if dir_path.is_dir():
            for file_path in dir_path.rglob("*.md"):
                check_file_for_banned_phrases(file_path, display_name)

    return result
