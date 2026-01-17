# swarm/tools/validation/validators/skills.py
"""
FR-004: Skill File Validation

Validates that skills declared in agent frontmatter have valid SKILL.md files.

Checks:
- Skill file exists at .claude/skills/<skill>/SKILL.md
- Skill frontmatter contains required fields (name, description)
"""

from typing import Set

from swarm.validator import SimpleYAMLParser, ValidationResult
from swarm.tools.validation.helpers import ROOT, AGENTS_DIR, SKILLS_DIR


def validate_skills() -> ValidationResult:
    """
    Validate that skills declared in agent frontmatter have valid SKILL.md files.

    Checks:
    - Skill file exists
    - Skill frontmatter is valid (name, description)
    """
    result = ValidationResult()

    if not SKILLS_DIR.is_dir():
        return result

    # Collect all declared skills from agents
    declared_skills: Set[str] = set()
    if AGENTS_DIR.is_dir():
        for agent_path in AGENTS_DIR.glob("*.md"):
            if agent_path.is_symlink():
                # Skip symlinks: validation only applies to real files
                continue
            try:
                content = agent_path.read_text(encoding="utf-8")
                fm = SimpleYAMLParser.parse(content)
                if "skills" in fm and isinstance(fm["skills"], list):
                    # Type ignore: fm from YAML parser returns Any; we know skills are strings
                    skills_list: list[str] = [str(s) for s in fm["skills"]]  # type: ignore[misc]
                    declared_skills.update(skills_list)
            except Exception:
                pass

    # Check each declared skill has a valid file
    for skill_name in declared_skills:
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"

        if not skill_file.is_file():
            result.add_error(
                "SKILL",
                f"skill '{skill_name}'",
                f"declared by agents but {skill_file.relative_to(ROOT)} does not exist",
                f"Create {skill_file.relative_to(ROOT)} with valid frontmatter (name, description)",
                file_path=str(skill_file)
            )
            continue

        # Validate skill frontmatter
        try:
            content = skill_file.read_text(encoding="utf-8")
            fm = SimpleYAMLParser.parse(content)

            if "name" not in fm or not fm.get("name", "").strip():
                result.add_error(
                    "SKILL",
                    str(skill_file.relative_to(ROOT)),
                    "missing required field 'name'",
                    f"Add `name: {skill_name}` to frontmatter",
                    file_path=str(skill_file)
                )

            if "description" not in fm or not fm.get("description", "").strip():
                result.add_error(
                    "SKILL",
                    str(skill_file.relative_to(ROOT)),
                    "missing required field 'description'",
                    "Add `description: <skill description>` to frontmatter",
                    file_path=str(skill_file)
                )
        except ValueError as e:
            result.add_error(
                "SKILL",
                str(skill_file.relative_to(ROOT)),
                f"malformed YAML in skill frontmatter: {e}",
                "Check YAML syntax in skill frontmatter",
                file_path=str(skill_file)
            )

    return result
