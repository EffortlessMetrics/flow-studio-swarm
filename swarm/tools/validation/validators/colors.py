# swarm/tools/validation/validators/colors.py
"""
FR-002b: Color Validation

Validates that agent colors match expected colors for their role_family.

LEGACY: This check is skipped if .claude/agents/ directory does not exist.
The new architecture uses swarm/config/agents/ for agent configuration instead.

Checks:
- Agent frontmatter has 'color' field
- Color is valid (in VALID_COLORS)
- Color matches expected color for the agent's role_family in AGENTS.md
"""

from typing import Any, Dict

from swarm.validator import SimpleYAMLParser, ValidationResult
from swarm.tools.validation.helpers import AGENTS_DIR, ROOT, safe_get_stripped
from swarm.tools.validation.constants import ROLE_FAMILY_COLOR_MAP, VALID_COLORS


def validate_colors(registry: Dict[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate that agent colors match expected colors for their role_family.

    LEGACY: This check is skipped if .claude/agents/ directory does not exist.
    The new architecture uses swarm/config/agents/ for agent configuration instead.

    Checks:
    - Agent frontmatter has 'color' field
    - Color is valid (in VALID_COLORS)
    - Color matches expected color for the agent's role_family in AGENTS.md
    """
    result = ValidationResult()

    # LEGACY: Skip color check if .claude/agents/ doesn't exist
    # The new architecture uses swarm/config/agents/ instead
    if not AGENTS_DIR.is_dir():
        return result

    # Check each agent file
    for path in sorted(AGENTS_DIR.glob("*.md")):
        if path.is_symlink():
            # Skip symlinks: validation only applies to real files
            continue

        filename_key = path.stem
        rel_path = path.relative_to(ROOT)

        # Get expected color from registry
        if filename_key not in registry:
            continue

        agent_meta = registry[filename_key]
        if "role_family" not in agent_meta:
            # Registry hasn't been updated with role_family yet; skip color check
            continue

        role_family = agent_meta.get("role_family", "").strip().lower()
        expected_color = ROLE_FAMILY_COLOR_MAP.get(role_family)

        if not expected_color:
            # Unknown role family
            result.add_warning(
                "COLOR",
                str(rel_path),
                f"unknown role_family '{role_family}' in AGENTS.md (cannot validate color)",
                "Ensure role_family is one of: " + ", ".join(ROLE_FAMILY_COLOR_MAP.keys()),
                file_path=str(path)
            )
            continue

        # Parse frontmatter
        try:
            content = path.read_text(encoding="utf-8")
            fm = SimpleYAMLParser.parse(content, path)
        except Exception:
            # Skip color check if frontmatter parsing failed (already reported)
            continue

        # Check for color field
        if "color" not in fm:
            result.add_error(
                "COLOR",
                str(rel_path),
                f"missing required field 'color' (expected '{expected_color}' for role family '{role_family}')",
                f"Add `color: {expected_color}` to frontmatter",
                file_path=str(path)
            )
            continue

        color_value = safe_get_stripped(fm.get("color"))
        color = color_value.lower() if color_value else ""

        # Validate color value
        if color and color not in VALID_COLORS:
            result.add_error(
                "COLOR",
                str(rel_path),
                f"invalid color value '{color}' (expected one of: {', '.join(VALID_COLORS)})",
                f"Change `color: {color}` to a valid color",
                file_path=str(path)
            )
            continue

        # Check color matches expected color for role family
        if color != expected_color:
            result.add_error(
                "COLOR",
                str(rel_path),
                f"color '{color}' does not match expected color '{expected_color}' for role family '{role_family}'",
                f"Change `color: {color}` to `color: {expected_color}` to match role family in AGENTS.md",
                file_path=str(path)
            )

    return result
