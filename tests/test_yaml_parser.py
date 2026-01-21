"""
Test suite for SimpleYAMLParser strict mode behavior.

Tests the parser's handling of malformed YAML lines,
especially in strict mode.
"""

import sys
from pathlib import Path

import pytest

# Import the validator to access SimpleYAMLParser
sys.path.insert(0, str(Path(__file__).parent.parent / "swarm" / "tools"))
from validate_swarm import SimpleYAMLParser

# ============================================================================
# Test: Malformed YAML in Normal Mode (lenient)
# ============================================================================


def test_parser_ignores_junk_lines_in_normal_mode():
    """
    Test: SimpleYAMLParser ignores malformed lines in normal (non-strict) mode.

    Given: Frontmatter with a malformed line
    When: I parse with strict=False (default)
    Then: It should skip the malformed line and parse successfully
    """
    content = """---
name: test-agent
description: A test agent
junk line with no colon here
color: blue
---

Body content."""

    # Should parse without error in normal mode
    result = SimpleYAMLParser.parse(content, strict=False)

    assert result["name"] == "test-agent"
    assert result["description"] == "A test agent"
    assert result["color"] == "blue"
    # Junk line is silently skipped


def test_parser_handles_comments_normally():
    """
    Test: SimpleYAMLParser correctly handles comment lines.

    Given: Frontmatter with comments and valid fields
    When: I parse
    Then: Comments should be ignored, fields should be parsed
    """
    content = """---
# This is a comment
name: test-agent
# Another comment
description: A test agent
color: blue
# End comment
---

Body."""

    result = SimpleYAMLParser.parse(content, strict=False)

    assert result["name"] == "test-agent"
    assert result["description"] == "A test agent"
    assert result["color"] == "blue"


def test_parser_handles_empty_lines_normally():
    """
    Test: SimpleYAMLParser correctly handles empty lines in frontmatter.

    Given: Frontmatter with empty lines between fields
    When: I parse
    Then: Empty lines should be ignored
    """
    content = """---
name: test-agent

description: A test agent

color: blue
---

Body."""

    result = SimpleYAMLParser.parse(content, strict=False)

    assert result["name"] == "test-agent"
    assert result["description"] == "A test agent"
    assert result["color"] == "blue"


# ============================================================================
# Test: Malformed YAML in Strict Mode
# ============================================================================


def test_parser_errors_on_junk_lines_in_strict_mode():
    """
    Test: SimpleYAMLParser errors on malformed lines in strict mode.

    Given: Frontmatter with a malformed (non-comment) line
    When: I parse with strict=True
    Then: It should raise ValueError
    """
    content = """---
name: test-agent
description: A test agent
junk line with no colon here
color: blue
---

Body content."""

    # Should raise error in strict mode
    with pytest.raises(ValueError, match="Malformed YAML on line"):
        SimpleYAMLParser.parse(content, strict=True)


def test_parser_allows_comments_in_strict_mode():
    """
    Test: SimpleYAMLParser allows comments in strict mode.

    Given: Frontmatter with valid fields and comments
    When: I parse with strict=True
    Then: Comments should be allowed, no error
    """
    content = """---
# Comment line is OK
name: test-agent
description: A test agent  # inline comment (if supported)
color: blue
---

Body."""

    # Should parse without error in strict mode (comments are allowed)
    result = SimpleYAMLParser.parse(content, strict=True)

    assert result["name"] == "test-agent"
    assert result["description"] == "A test agent  # inline comment (if supported)"
    assert result["color"] == "blue"


def test_parser_allows_empty_lines_in_strict_mode():
    """
    Test: SimpleYAMLParser allows empty lines in strict mode.

    Given: Frontmatter with empty lines
    When: I parse with strict=True
    Then: Empty lines should be allowed, no error
    """
    content = """---
name: test-agent

description: A test agent

color: blue
---

Body."""

    # Should parse without error in strict mode
    result = SimpleYAMLParser.parse(content, strict=True)

    assert result["name"] == "test-agent"
    assert result["description"] == "A test agent"
    assert result["color"] == "blue"


def test_parser_errors_on_multiple_malformed_lines():
    """
    Test: SimpleYAMLParser reports first malformed line in strict mode.

    Given: Frontmatter with multiple malformed lines
    When: I parse with strict=True
    Then: It should error on the first malformed line
    """
    content = """---
name: test-agent
this is junk
description: A test agent
more junk here
color: blue
---

Body."""

    # Should raise error on first malformed line
    with pytest.raises(ValueError, match="Malformed YAML on line.*this is junk"):
        SimpleYAMLParser.parse(content, strict=True)


def test_parser_errors_with_helpful_message():
    """
    Test: SimpleYAMLParser provides helpful error message on malformed line.

    Given: Frontmatter with malformed line
    When: I parse with strict=True
    Then: Error message should show the problematic line
    """
    content = """---
name: test-agent
this_line_has_underscores_but_no_colon
color: blue
---

Body."""

    with pytest.raises(ValueError) as exc_info:
        SimpleYAMLParser.parse(content, strict=True)

    error_msg = str(exc_info.value)
    assert "Malformed YAML" in error_msg
    assert "this_line_has_underscores_but_no_colon" in error_msg


# ============================================================================
# Test: Valid YAML Patterns
# ============================================================================


def test_parser_handles_lists_in_strict_mode():
    """
    Test: SimpleYAMLParser handles multi-line lists in strict mode.

    Given: Frontmatter with multi-line list
    When: I parse with strict=True
    Then: List should be parsed correctly
    """
    content = """---
name: test-agent
description: A test agent
color: blue
skills:
  - skill-one
  - skill-two
---

Body."""

    result = SimpleYAMLParser.parse(content, strict=True)

    assert result["name"] == "test-agent"
    assert result["skills"] == ["skill-one", "skill-two"]


def test_parser_handles_inline_lists_in_strict_mode():
    """
    Test: SimpleYAMLParser handles inline lists in strict mode.

    Given: Frontmatter with inline list
    When: I parse with strict=True
    Then: List should be parsed correctly
    """
    content = """---
name: test-agent
description: A test agent
color: blue
skills: [skill-one, skill-two]
---

Body."""

    result = SimpleYAMLParser.parse(content, strict=True)

    assert result["name"] == "test-agent"
    assert result["skills"] == ["skill-one", "skill-two"]


def test_parser_handles_quoted_values_in_strict_mode():
    """
    Test: SimpleYAMLParser handles quoted values in strict mode.

    Given: Frontmatter with quoted field values
    When: I parse with strict=True
    Then: Quoted values should be parsed correctly (quotes removed)
    """
    content = """---
name: "test-agent"
description: 'A test agent'
color: blue
---

Body."""

    result = SimpleYAMLParser.parse(content, strict=True)

    assert result["name"] == "test-agent"
    assert result["description"] == "A test agent"
    assert result["color"] == "blue"


# ============================================================================
# Test: Integration with Validator (Strict Mode Enforcement)
# ============================================================================


def test_validator_enforces_strict_yaml_in_strict_mode(tmp_path, monkeypatch):
    """
    Integration: Validator enforces strict YAML when --strict flag is set.

    Given: An agent file with malformed YAML
    When: The validator's frontmatter check runs with strict=True
    Then: It should report a YAML parse error
    """
    # Create minimal structure
    (tmp_path / "swarm").mkdir()
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    (tmp_path / "swarm" / "AGENTS.md").write_text("""# Agent Registry

| Key | Flows | Role Family | Color | Source | Short Role |
|-----|-------|-------------|-------|--------|------------|
| bad-agent | 1 | implementation | green | project | Bad agent |
""")

    # Create agent with malformed YAML
    bad_agent_file = tmp_path / ".claude" / "agents" / "bad-agent.md"
    bad_agent_file.write_text("""---
name: bad-agent
description: An agent with bad YAML
this_line_has_no_colon_value_pair
color: green
model: inherit
---

You are a bad agent.
""")

    # Import the frontmatter validator module and helpers
    from swarm.tools.validation.validators import frontmatter as frontmatter_module
    from swarm.tools.validation import helpers

    # Use monkeypatch to patch the module-level constants in the frontmatter module
    # This is necessary because frontmatter.py imports AGENTS_DIR directly,
    # so we need to patch it where it's used, not where it's defined
    monkeypatch.setattr(frontmatter_module, "AGENTS_DIR", tmp_path / ".claude" / "agents")
    monkeypatch.setattr(frontmatter_module, "ROOT", tmp_path)

    # Run frontmatter validation with strict_mode=True
    # Pass an empty registry since we're just testing YAML parsing
    result = frontmatter_module.validate_frontmatter({}, strict_mode=True)

    # Should have an error due to malformed YAML
    assert result.has_errors(), f"Expected validation errors, got none. Warnings: {result.warnings}"

    # Check that the error mentions YAML parsing issue
    # ValidationError uses 'problem' attribute, not 'message'
    error_problems = [e.problem for e in result.errors]
    yaml_error_found = any(
        "Malformed YAML" in prob or "YAML parse error" in prob
        for prob in error_problems
    )
    assert yaml_error_found, \
        f"Expected YAML error in messages, got: {error_problems}"
