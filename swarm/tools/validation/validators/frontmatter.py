# swarm/tools/validation/validators/frontmatter.py
"""
FR-002: Frontmatter Validation

Validates YAML frontmatter in all agent files.

LEGACY: This check is skipped if .claude/agents/ directory does not exist.
The new architecture uses swarm/config/agents/ for agent configuration instead.

Checks:
- YAML parses correctly
- Required fields present (name, description, model)
- Name matches filename
- Model is valid
- Swarm design constraint fields (tools, permissionMode): WARN in default mode, ERROR in strict mode
- Skills is a list if present
"""

from typing import Any, Dict

from swarm.validator import SimpleYAMLParser, ValidationResult
from swarm.tools.validation.helpers import AGENTS_DIR, ROOT, safe_get_stripped
from swarm.tools.validation.constants import VALID_MODELS


def validate_frontmatter(_registry: Dict[str, Dict[str, Any]], strict_mode: bool = False) -> ValidationResult:
    """
    Validate YAML frontmatter in all agent files.

    LEGACY: This check is skipped if .claude/agents/ directory does not exist.
    The new architecture uses swarm/config/agents/ for agent configuration instead.

    Checks:
    - YAML parses correctly
    - Required fields present (name, description, model)
    - Name matches filename
    - Model is valid
    - Swarm design constraint fields (tools, permissionMode): WARN in default mode, ERROR in strict mode
    - Skills is a list if present

    Args:
        _registry: Agent registry from AGENTS.md (reserved for future registry-based validation)
        strict_mode: If True, treat swarm design constraint violations as errors
    """
    result = ValidationResult()

    # LEGACY: Skip frontmatter check if .claude/agents/ doesn't exist
    # The new architecture uses swarm/config/agents/ instead
    if not AGENTS_DIR.is_dir():
        return result

    for path in sorted(AGENTS_DIR.glob("*.md")):
        if path.is_symlink():
            # Skip symlinks: validation only applies to real files
            continue

        filename_key = path.stem
        rel_path = path.relative_to(ROOT)

        # Parse frontmatter
        try:
            content = path.read_text(encoding="utf-8")
            fm = SimpleYAMLParser.parse(content, path, strict=strict_mode)
        except ValueError as e:
            result.add_error(
                "FRONTMATTER",
                str(rel_path),
                f"YAML parse error: {e}",
                "Check YAML syntax; ensure frontmatter starts and ends with '---'",
                file_path=str(path)
            )
            continue
        except Exception as e:
            result.add_error(
                "FRONTMATTER",
                str(rel_path),
                f"unexpected error: {e}",
                "Check file encoding and YAML syntax",
                file_path=str(path)
            )
            continue

        # Required fields (with null-safety for YAML tilde values)
        name_value = safe_get_stripped(fm.get("name"))
        if not name_value:
            result.add_error(
                "FRONTMATTER",
                str(rel_path),
                "missing required field 'name'",
                f"Add `name: {filename_key}` to frontmatter",
                file_path=str(path)
            )

        description_value = safe_get_stripped(fm.get("description"))
        if not description_value:
            result.add_error(
                "FRONTMATTER",
                str(rel_path),
                "missing required field 'description'",
                "Add `description: <one-line description>` to frontmatter",
                file_path=str(path)
            )

        model_value = safe_get_stripped(fm.get("model"))
        if not model_value:
            result.add_error(
                "FRONTMATTER",
                str(rel_path),
                "missing required field 'model'",
                "Add `model: inherit` to frontmatter",
                file_path=str(path)
            )

        # Name must match filename
        if name_value and name_value != filename_key:
            result.add_error(
                "FRONTMATTER",
                str(rel_path),
                f"frontmatter 'name' field '{name_value}' does not match filename '{filename_key}'",
                f"Change `name: {name_value}` to `name: {filename_key}`, or rename file to {name_value}.md",
                file_path=str(path)
            )

        # Model must be valid
        if model_value and model_value not in VALID_MODELS:
            result.add_error(
                "FRONTMATTER",
                str(rel_path),
                f"invalid model value '{model_value}' (must be one of {VALID_MODELS})",
                f"Change `model: {model_value}` to one of: {', '.join(VALID_MODELS)}",
                file_path=str(path)
            )

        # Swarm design constraint fields (Layer 2 constraint)
        # Layer 1 (Claude Code platform): supports 'tools' and 'permissionMode'
        # Layer 2 (This swarm design): intentionally omits them, uses prompt-based constraints
        # Default mode: WARN (design guideline, not error)
        # Strict mode: ERROR (enforce swarm design)
        if "tools" in fm:
            if strict_mode:
                result.add_error(
                    "FRONTMATTER",
                    str(rel_path),
                    "field 'tools' violates swarm design constraint (use --strict to enforce)",
                    "Remove 'tools:' field; this swarm uses prompt-based constraints, not tool denial",
                    file_path=str(path)
                )
            else:
                result.add_warning(
                    "FRONTMATTER",
                    str(rel_path),
                    "field 'tools' found (swarm design guideline: omit this field)",
                    "Consider removing 'tools:' field; this swarm uses prompt-based constraints",
                    file_path=str(path)
                )

        if "permissionMode" in fm:
            if strict_mode:
                result.add_error(
                    "FRONTMATTER",
                    str(rel_path),
                    "field 'permissionMode' violates swarm design constraint (use --strict to enforce)",
                    "Remove 'permissionMode:' field; this swarm enforces permissions at repo level",
                    file_path=str(path)
                )
            else:
                result.add_warning(
                    "FRONTMATTER",
                    str(rel_path),
                    "field 'permissionMode' found (swarm design guideline: omit this field)",
                    "Consider removing 'permissionMode:' field; this swarm enforces permissions at repo level",
                    file_path=str(path)
                )

        # Skills must be a list
        if "skills" in fm:
            skills = fm["skills"]
            if not isinstance(skills, list):
                result.add_error(
                    "FRONTMATTER",
                    str(rel_path),
                    f"'skills' must be a list (got {type(skills).__name__})",
                    "Change skills to list format: `skills: [skill1, skill2]` or use multi-line list",
                    file_path=str(path)
                )

    return result
