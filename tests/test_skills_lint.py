"""
Test suite for skills_lint.py validator.

Tests the SkillsValidator class which validates .claude/skills/*/SKILL.md files
for correct structure and YAML metadata.
"""

# Import the module under test
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "swarm" / "tools"))
from skills_lint import SkillsValidator

# ============================================================================
# Happy Path Tests
# ============================================================================


def test_valid_skill_file(tmp_path):
    """
    Valid skill file passes validation.

    Given: A skill file with valid YAML frontmatter (name and description)
    When: I run the validator
    Then: Validation passes with no errors
    """
    # Create skills directory structure
    skill_dir = tmp_path / ".claude" / "skills" / "test-runner"
    skill_dir.mkdir(parents=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-runner
description: Execute test suites and produce test summaries
---

This is the test-runner skill.
""")

    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is True
    assert errors == []


def test_multiple_valid_skills(tmp_path):
    """
    Multiple valid skill files all pass validation.

    Given: Multiple skill files with valid YAML frontmatter
    When: I run the validator
    Then: All skills pass validation
    """
    skills = ["test-runner", "auto-linter", "policy-runner"]

    for skill_name in skills:
        skill_dir = tmp_path / ".claude" / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(f"""---
name: {skill_name}
description: Description for {skill_name}
---

This is the {skill_name} skill.
""")

    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is True
    assert errors == []


def test_no_skills_directory(tmp_path):
    """
    Missing skills directory is acceptable (no skills to validate).

    Given: No .claude/skills directory exists
    When: I run the validator
    Then: Validation passes (no skills, OK)
    """
    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is True
    assert errors == []


# ============================================================================
# Error Path Tests
# ============================================================================


def test_missing_frontmatter_start_marker(tmp_path):
    """
    Skill file without opening --- marker fails validation.

    Given: A skill file that doesn't start with ---
    When: I run the validator
    Then: Validation fails with missing frontmatter error
    """
    skill_dir = tmp_path / ".claude" / "skills" / "bad-skill"
    skill_dir.mkdir(parents=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""name: bad-skill
description: Missing opening delimiter
---

Content.
""")

    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert len(errors) == 1
    assert "bad-skill" in errors[0]
    assert "Missing YAML frontmatter" in errors[0]


def test_missing_frontmatter_end_marker(tmp_path):
    """
    Skill file without closing --- marker fails validation.

    Given: A skill file with opening --- but no closing ---
    When: I run the validator
    Then: Validation fails (either unterminated or YAML parse error)
    """
    skill_dir = tmp_path / ".claude" / "skills" / "incomplete-skill"
    skill_dir.mkdir(parents=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: incomplete-skill
description: Missing closing delimiter

Content without closing ---.
""")

    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert len(errors) == 1
    assert "incomplete-skill" in errors[0]
    # May report as "Unterminated" or as YAML parse error depending on content
    assert "Unterminated" in errors[0] or "YAML" in errors[0]


def test_missing_required_field_name(tmp_path):
    """
    Skill file missing 'name' field fails validation.

    Given: A skill file with valid YAML but missing 'name'
    When: I run the validator
    Then: Validation fails with missing name error
    """
    skill_dir = tmp_path / ".claude" / "skills" / "nameless"
    skill_dir.mkdir(parents=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
description: Skill without a name field
---

Content.
""")

    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert any("name" in e for e in errors)


def test_missing_required_field_description(tmp_path):
    """
    Skill file missing 'description' field fails validation.

    Given: A skill file with valid YAML but missing 'description'
    When: I run the validator
    Then: Validation fails with missing description error
    """
    skill_dir = tmp_path / ".claude" / "skills" / "nodesc"
    skill_dir.mkdir(parents=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: nodesc
---

Content without description.
""")

    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert any("description" in e for e in errors)


def test_empty_frontmatter(tmp_path):
    """
    Skill file with empty frontmatter block fails validation.

    Given: A skill file with empty YAML frontmatter
    When: I run the validator
    Then: Validation fails with empty frontmatter error
    """
    skill_dir = tmp_path / ".claude" / "skills" / "empty"
    skill_dir.mkdir(parents=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
---

Empty frontmatter.
""")

    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert any("Empty" in e for e in errors)


def test_malformed_yaml(tmp_path):
    """
    Skill file with malformed YAML fails validation.

    Given: A skill file with invalid YAML syntax
    When: I run the validator
    Then: Validation fails with YAML parse error
    """
    skill_dir = tmp_path / ".claude" / "skills" / "malformed"
    skill_dir.mkdir(parents=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: malformed
description: "Unclosed quote
---

Content.
""")

    validator = SkillsValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert any("YAML" in e or "parse" in e.lower() for e in errors)
