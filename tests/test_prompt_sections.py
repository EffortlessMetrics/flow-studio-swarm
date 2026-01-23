"""
Test suite for agent prompt section validation (FR-006).

Tests the validator's ability to ensure agent prompts include required sections:
- ## Inputs (or ## Input)
- ## Outputs (or ## Output)
- ## Behavior

BDD Scenarios covered:
- Agent missing ## Inputs fails in strict mode
- Agent missing ## Outputs fails in strict mode
- Agent missing ## Behavior fails in strict mode
- Agent with all required sections passes
- Agent with singular form (## Input, ## Output) passes
- In default mode (non-strict), missing sections are warnings not errors
- Check is disabled by default (requires --check-prompts flag)
"""

from conftest import (
    add_agent_to_registry,
    assert_error_contains,
    assert_error_type,
    assert_validator_failed,
    assert_validator_passed,
)

# ============================================================================
# Happy Path Tests
# ============================================================================


def test_agent_with_all_required_sections_passes(temp_repo, run_validator):
    """
    Agent with all required sections passes validation.

    Given: Agent file has ## Inputs, ## Outputs, and ## Behavior sections
    When: I run the validator with --check-prompts
    Then: Validator exits with code 0
    """
    add_agent_to_registry(temp_repo, "complete-agent")

    agent_file = temp_repo / ".claude" / "agents" / "complete-agent.md"
    agent_file.write_text("""---
name: complete-agent
description: Agent with all required sections
color: green
model: inherit
---

You are a test agent.

## Inputs

- `RUN_BASE/signal/input.md`

## Outputs

- `RUN_BASE/signal/output.md`

## Behavior

1. Read input
2. Process
3. Write output
""")

    result = run_validator(temp_repo, flags=["--check-prompts"])
    assert_validator_passed(result)


def test_agent_with_singular_form_sections_passes(temp_repo, run_validator):
    """
    Agent with singular form sections (## Input, ## Output) passes.

    Given: Agent file uses ## Input and ## Output (singular)
    When: I run the validator with --check-prompts
    Then: Validator exits with code 0
    """
    add_agent_to_registry(temp_repo, "singular-agent")

    agent_file = temp_repo / ".claude" / "agents" / "singular-agent.md"
    agent_file.write_text("""---
name: singular-agent
description: Agent with singular section names
color: green
model: inherit
---

You are a test agent.

## Input

- Single input file

## Output

- Single output file

## Behavior

Do something.
""")

    result = run_validator(temp_repo, flags=["--check-prompts"])
    assert_validator_passed(result)


# ============================================================================
# Missing Section Tests (Strict Mode - Errors)
# ============================================================================


def test_agent_missing_inputs_fails_strict(temp_repo, run_validator):
    """
    Agent missing ## Inputs fails in strict mode.

    Given: Agent file has ## Outputs and ## Behavior but not ## Inputs
    When: I run the validator with --check-prompts --strict
    Then: Validator exits with code 1
    And: Error message indicates missing ## Inputs
    """
    add_agent_to_registry(temp_repo, "no-inputs")

    agent_file = temp_repo / ".claude" / "agents" / "no-inputs.md"
    agent_file.write_text("""---
name: no-inputs
description: Agent missing inputs section
color: green
model: inherit
---

You are a test agent.

## Outputs

- Output file

## Behavior

Do something.
""")

    result = run_validator(temp_repo, flags=["--check-prompts", "--strict"])
    assert_validator_failed(result)
    assert_error_type(result.stderr, "PROMPT")
    assert_error_contains(result.stderr, "Inputs")


def test_agent_missing_outputs_fails_strict(temp_repo, run_validator):
    """
    Agent missing ## Outputs fails in strict mode.

    Given: Agent file has ## Inputs and ## Behavior but not ## Outputs
    When: I run the validator with --check-prompts --strict
    Then: Validator exits with code 1
    And: Error message indicates missing ## Outputs
    """
    add_agent_to_registry(temp_repo, "no-outputs")

    agent_file = temp_repo / ".claude" / "agents" / "no-outputs.md"
    agent_file.write_text("""---
name: no-outputs
description: Agent missing outputs section
color: green
model: inherit
---

You are a test agent.

## Inputs

- Input file

## Behavior

Do something.
""")

    result = run_validator(temp_repo, flags=["--check-prompts", "--strict"])
    assert_validator_failed(result)
    assert_error_type(result.stderr, "PROMPT")
    assert_error_contains(result.stderr, "Outputs")


def test_agent_missing_behavior_fails_strict(temp_repo, run_validator):
    """
    Agent missing ## Behavior fails in strict mode.

    Given: Agent file has ## Inputs and ## Outputs but not ## Behavior
    When: I run the validator with --check-prompts --strict
    Then: Validator exits with code 1
    And: Error message indicates missing ## Behavior
    """
    add_agent_to_registry(temp_repo, "no-behavior")

    agent_file = temp_repo / ".claude" / "agents" / "no-behavior.md"
    agent_file.write_text("""---
name: no-behavior
description: Agent missing behavior section
color: green
model: inherit
---

You are a test agent.

## Inputs

- Input file

## Outputs

- Output file
""")

    result = run_validator(temp_repo, flags=["--check-prompts", "--strict"])
    assert_validator_failed(result)
    assert_error_type(result.stderr, "PROMPT")
    assert_error_contains(result.stderr, "Behavior")


def test_agent_missing_all_sections_fails_strict(temp_repo, run_validator):
    """
    Agent missing all required sections fails in strict mode.

    Given: Agent file has only frontmatter and basic prompt text
    When: I run the validator with --check-prompts --strict
    Then: Validator exits with code 1
    And: Error message indicates all missing sections
    """
    add_agent_to_registry(temp_repo, "minimal-agent")

    agent_file = temp_repo / ".claude" / "agents" / "minimal-agent.md"
    agent_file.write_text("""---
name: minimal-agent
description: Agent with no required sections
color: green
model: inherit
---

You are a minimal test agent with no structured sections.
""")

    result = run_validator(temp_repo, flags=["--check-prompts", "--strict"])
    assert_validator_failed(result)
    assert_error_type(result.stderr, "PROMPT")
    # Should mention all three missing sections
    assert_error_contains(result.stderr, "Inputs")
    assert_error_contains(result.stderr, "Outputs")
    assert_error_contains(result.stderr, "Behavior")


# ============================================================================
# Default Mode Tests (Warnings, not Errors)
# ============================================================================


def test_agent_missing_sections_warns_default_mode(temp_repo, run_validator):
    """
    Agent missing sections produces warnings (not errors) in default mode.

    Given: Agent file is missing required sections
    When: I run the validator with --check-prompts (no --strict)
    Then: Validator exits with code 0 (warnings don't fail)
    And: Warnings are printed about missing sections
    """
    add_agent_to_registry(temp_repo, "warn-agent")

    agent_file = temp_repo / ".claude" / "agents" / "warn-agent.md"
    agent_file.write_text("""---
name: warn-agent
description: Agent that should get warnings
color: green
model: inherit
---

You are a test agent with no structured sections.
""")

    result = run_validator(temp_repo, flags=["--check-prompts"])
    # Should pass (warnings don't fail in default mode)
    assert_validator_passed(result)
    # But should contain warnings about missing sections
    assert "Inputs" in result.stderr or "Inputs" in result.stdout
    assert "Outputs" in result.stderr or "Outputs" in result.stdout
    assert "Behavior" in result.stderr or "Behavior" in result.stdout


# ============================================================================
# Check Disabled by Default Tests
# ============================================================================


def test_check_disabled_by_default(temp_repo, run_validator):
    """
    Prompt section check is disabled by default.

    Given: Agent file is missing required sections
    When: I run the validator WITHOUT --check-prompts
    Then: Validator exits with code 0
    And: No PROMPT errors or warnings are reported
    """
    add_agent_to_registry(temp_repo, "no-check-agent")

    agent_file = temp_repo / ".claude" / "agents" / "no-check-agent.md"
    agent_file.write_text("""---
name: no-check-agent
description: Agent that should not be checked
color: green
model: inherit
---

You are a test agent with no structured sections.
""")

    result = run_validator(temp_repo)  # No --check-prompts flag
    assert_validator_passed(result)
    # Should NOT contain any PROMPT errors
    assert "PROMPT" not in result.stderr


# ============================================================================
# Edge Cases
# ============================================================================


def test_case_insensitive_section_headers(temp_repo, run_validator):
    """
    Section headers should be case-insensitive.

    Given: Agent file uses mixed case section headers
    When: I run the validator with --check-prompts
    Then: Validator exits with code 0
    """
    add_agent_to_registry(temp_repo, "case-agent")

    agent_file = temp_repo / ".claude" / "agents" / "case-agent.md"
    agent_file.write_text("""---
name: case-agent
description: Agent with mixed case headers
color: green
model: inherit
---

You are a test agent.

## INPUTS

- Input file

## outputs

- Output file

## BehavioR

Do something.
""")

    result = run_validator(temp_repo, flags=["--check-prompts"])
    assert_validator_passed(result)


def test_sections_with_extra_whitespace(temp_repo, run_validator):
    """
    Section headers with trailing whitespace should pass.

    Given: Agent file has section headers with trailing spaces
    When: I run the validator with --check-prompts
    Then: Validator exits with code 0
    """
    add_agent_to_registry(temp_repo, "whitespace-agent")

    agent_file = temp_repo / ".claude" / "agents" / "whitespace-agent.md"
    # Note: trailing spaces after section headers
    agent_file.write_text("""---
name: whitespace-agent
description: Agent with whitespace in headers
color: green
model: inherit
---

You are a test agent.

## Inputs

- Input file

## Outputs

- Output file

## Behavior

Do something.
""")

    result = run_validator(temp_repo, flags=["--check-prompts"])
    assert_validator_passed(result)


def test_similar_but_not_exact_headers_fail(temp_repo, run_validator):
    """
    Headers similar to but not matching required patterns should fail.

    Given: Agent file has "## Input Files" instead of "## Inputs"
    When: I run the validator with --check-prompts --strict
    Then: Validator fails because exact pattern not matched
    """
    add_agent_to_registry(temp_repo, "wrong-headers")

    agent_file = temp_repo / ".claude" / "agents" / "wrong-headers.md"
    agent_file.write_text("""---
name: wrong-headers
description: Agent with wrong header format
color: green
model: inherit
---

You are a test agent.

## Input Files

- Input file

## Output Artifacts

- Output file

## Agent Behavior

Do something.
""")

    result = run_validator(temp_repo, flags=["--check-prompts", "--strict"])
    assert_validator_failed(result)
    assert_error_type(result.stderr, "PROMPT")
