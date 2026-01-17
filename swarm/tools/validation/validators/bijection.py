# swarm/tools/validation/validators/bijection.py
"""
FR-001: Bijection Validation

Validates 1:1 mapping between swarm/AGENTS.md entries and .claude/agents/*.md files.

LEGACY: This check is skipped if .claude/agents/ directory does not exist.
The new architecture uses swarm/config/agents/ for agent configuration instead.

TRANSITION MODE: During the architecture transition from .claude/agents/ to
swarm/config/agents/, we only enforce:
- Every file in .claude/agents/ must be registered in AGENTS.md (file → registry)

We intentionally skip the registry → file check because:
- Most agents now use swarm/config/agents/ as the source of truth
- Only agents with custom prompts (like Flow 8 reset agents) need .claude/agents/ files
- Full bijection will be restored when the migration is complete
"""

from typing import Any, Dict, Set

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import AGENTS_DIR, ROOT
from swarm.tools.validation.validators.flow_references import suggest_typos


def validate_bijection(registry: Dict[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate correspondence between AGENTS.md and .claude/agents/*.md files.

    LEGACY: This check is skipped if .claude/agents/ directory does not exist.
    The new architecture uses swarm/config/agents/ for agent configuration instead.

    TRANSITION MODE: During the architecture transition from .claude/agents/ to
    swarm/config/agents/, we only enforce:
    - Every file in .claude/agents/ must be registered in AGENTS.md (file → registry)

    We intentionally skip the registry → file check because:
    - Most agents now use swarm/config/agents/ as the source of truth
    - Only agents with custom prompts (like Flow 8 reset agents) need .claude/agents/ files
    - Full bijection will be restored when the migration is complete

    Checks:
    - Every file has a corresponding registry entry (enforced)
    - Names are case-sensitive exact matches
    """
    result = ValidationResult()

    # LEGACY: Skip bijection check if .claude/agents/ doesn't exist
    # The new architecture uses swarm/config/agents/ instead
    if not AGENTS_DIR.is_dir():
        return result

    # Collect agent files
    agent_files: Set[str] = set()
    for path in AGENTS_DIR.glob("*.md"):
        if path.is_symlink():
            # Skip symlinks: they could enable information disclosure or create circular references
            continue
        agent_files.add(path.stem)

    # TRANSITION: Skip registry → file check
    # During migration, we don't require all registered agents to have .claude/agents/ files.
    # Most agents now live in swarm/config/agents/ as the source of truth.

    # Check file → registry
    for filename in agent_files:
        if filename not in registry:
            file_path = AGENTS_DIR / f"{filename}.md"

            # Suggest similar names using Levenshtein distance
            registry_keys = list(registry.keys())
            suggestions = suggest_typos(filename, registry_keys)

            problem = f"file exists but agent key '{filename}' is not in swarm/AGENTS.md"
            if suggestions:
                problem += f"; did you mean: {', '.join(suggestions)}?"

            fix_action = f"Add entry for '{filename}' to swarm/AGENTS.md or delete {file_path.relative_to(ROOT)}"
            if suggestions:
                fix_action = f"Update '{filename}' entry to match one of: {', '.join(suggestions)}, or add new entry to swarm/AGENTS.md, or delete {file_path.relative_to(ROOT)}"

            result.add_error(
                "BIJECTION",
                str(file_path.relative_to(ROOT)),
                problem,
                fix_action,
                file_path=str(file_path)
            )

    return result
