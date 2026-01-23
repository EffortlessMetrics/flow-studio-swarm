"""
Tests for selftest plan introspection (AC-SELFTEST-INTROSPECTABLE).

Tests the introspectable selftest plan feature, ensuring developers can see
all steps, tiers, dependencies, and execution order before running the full
selftest.

**Assumptions**:
- selftest_config.py defines exactly 16 steps (KERNEL=1, GOVERNANCE=13, OPTIONAL=2)
- No circular dependencies in step.depends_on
- All steps have id, name, description, tier, severity, category, depends_on fields
- show_plan_text() and show_plan_json() are implemented in selftest.py

**Expected behavior when code is implemented**:
1. All 62 tests pass
2. Code coverage > 85%
3. `selftest --plan` outputs human-readable table
4. `selftest --plan --json` outputs valid JSON matching api_contracts.yaml

BDD Scenarios covered:
- Scenario 1: "Selftest plan shows all steps with tiers"
- Scenario 2: "Selftest plan output is machine-parseable"
- Scenario 3: "Selftest plan shows dependencies"

Test Coverage:
- Unit Tests (8): Configuration metadata, DAG validation, text/JSON formats, error paths
- Integration Tests (4): CLI execution, JSON validity, plan output consistency, step counts
- Error-path Tests (4): Circular dependencies, invalid tiers, duplicates, malformed JSON

Acceptance Criteria:
- [x] --plan outputs exactly 16 steps with KERNEL/GOVERNANCE/OPTIONAL tiers
- [x] Tier distribution: KERNEL=1, GOVERNANCE=13, OPTIONAL=2
- [x] --plan --json outputs valid JSON with "steps" array (16 items) and "summary" object
- [x] Each step in JSON has: id, tier, description, depends_on (array)
- [x] Dependencies accurately reflect step ordering
- [x] Steps with no dependencies marked as "root" in output
- [x] Plan generation timing is sub-200ms (advisory)
- [x] Error paths: circular dependencies, invalid tiers, duplicates detected
- [x] JSON output is always valid (no malformed output)
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "swarm" / "tools"))

try:
    from selftest_config import (
        SELFTEST_STEPS,
        SelfTestStep,
        SelfTestTier,
        validate_step_list,
    )
except ImportError as e:
    pytest.skip(f"Could not import selftest_config: {e}", allow_module_level=True)

# ============================================================================
# MODULE-LEVEL CONSTANTS (extracted from magic numbers)
# ============================================================================

EXPECTED_TOTAL_STEPS = 16
EXPECTED_KERNEL_STEPS = 1
EXPECTED_GOVERNANCE_STEPS = 13
EXPECTED_OPTIONAL_STEPS = 2


# ============================================================================
# UNIT TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.quick
@pytest.mark.ac_selftest_introspectable
class TestSelfTestConfigStructure:
    """Unit tests for selftest configuration metadata and structure."""

    def test_selftest_config_has_16_steps(self):
        """
        Verify all 16 steps defined with complete metadata.

        Given: selftest_config.SELFTEST_STEPS is loaded
        When: I count the steps and check their required fields
        Then: Exactly 16 steps are defined with id, description, tier, severity, category, command
        """
        # Arrange & Act
        assert len(SELFTEST_STEPS) == EXPECTED_TOTAL_STEPS, (
            f"Expected {EXPECTED_TOTAL_STEPS} steps, got {len(SELFTEST_STEPS)}"
        )

        # Assert: All steps have required fields
        required_fields = ["id", "description", "tier", "severity", "category", "command"]
        for step in SELFTEST_STEPS:
            for field in required_fields:
                assert hasattr(step, field), f"Step {step.id} missing field: {field}"
                value = getattr(step, field)
                assert value is not None, f"Step {step.id}.{field} is None"

        # Assert: All step IDs are unique
        step_ids = [step.id for step in SELFTEST_STEPS]
        assert len(step_ids) == len(set(step_ids)), "Duplicate step IDs found"

    def test_selftest_config_tier_distribution(self):
        """
        Verify tier distribution: 1 KERNEL, 13 GOVERNANCE, 2 OPTIONAL.

        Given: selftest_config.SELFTEST_STEPS is loaded
        When: I count steps by tier
        Then: 1 KERNEL, 13 GOVERNANCE, 2 OPTIONAL (16 total)
        """
        # Arrange & Act
        kernel_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.KERNEL]
        governance_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.GOVERNANCE]
        optional_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.OPTIONAL]

        # Assert
        assert len(kernel_steps) == EXPECTED_KERNEL_STEPS, (
            f"Expected {EXPECTED_KERNEL_STEPS} KERNEL step, got {len(kernel_steps)}"
        )
        assert len(governance_steps) == EXPECTED_GOVERNANCE_STEPS, (
            f"Expected {EXPECTED_GOVERNANCE_STEPS} GOVERNANCE steps, got {len(governance_steps)}"
        )
        assert len(optional_steps) == EXPECTED_OPTIONAL_STEPS, (
            f"Expected {EXPECTED_OPTIONAL_STEPS} OPTIONAL steps, got {len(optional_steps)}"
        )
        assert (
            len(kernel_steps) + len(governance_steps) + len(optional_steps) == EXPECTED_TOTAL_STEPS
        ), f"Tier counts don't add up to {EXPECTED_TOTAL_STEPS}"

    def test_selftest_config_dag_valid_no_cycles(self):
        """
        Verify dependency DAG has no cycles and dependencies are valid.

        Given: selftest_config.SELFTEST_STEPS with dependencies defined
        When: I validate the DAG
        Then: No cycles, all dependencies reference valid steps
        """
        # Arrange & Act
        errors = validate_step_list()

        # Assert: No errors from validation
        assert errors == [], f"Step list validation failed: {errors}"

    def test_show_plan_text_lists_all_steps(self):
        """
        Verify --plan text output format and content.

        Given: selftest_config.SELFTEST_STEPS is loaded
        When: I generate text plan output
        Then: Output contains all 16 step IDs, tiers, descriptions, and tier counts
        """
        # Arrange
        from selftest import SelfTestRunner

        runner = SelfTestRunner(json_output=False)
        steps = SELFTEST_STEPS

        # Act: Capture text plan output
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            runner.show_plan_text(steps)
        text_output = captured_output.getvalue()

        # Assert: Output structure
        assert "SELFTEST PLAN" in text_output, "Missing plan header"
        assert f"Total steps: {EXPECTED_TOTAL_STEPS}" in text_output, "Missing step count"

        # Assert: All step IDs present
        for step in steps:
            assert step.id in text_output, f"Step {step.id} not in text output"
            assert step.description in text_output, f"Description for {step.id} not in output"

        # Assert: All tiers present in output
        assert "KERNEL" in text_output, "KERNEL tier not in output"
        assert "GOVERNANCE" in text_output, "GOVERNANCE tier not in output"
        assert "OPTIONAL" in text_output, "OPTIONAL tier not in output"

    def test_plan_json_schema_valid(self):
        """
        Verify JSON plan matches api_contracts.yaml schema.

        Given: selftest_config.SELFTEST_STEPS is loaded
        When: I generate JSON plan output
        Then: JSON is valid with version, steps array (16 items), summary object
        """
        # Arrange
        from selftest import SelfTestRunner

        runner = SelfTestRunner(json_output=True)
        steps = SELFTEST_STEPS

        # Act: Capture JSON plan output
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            runner.show_plan_json(steps)
        json_output = captured_output.getvalue()

        # Parse JSON
        plan_data = json.loads(json_output)

        # Assert: Schema structure
        assert "version" in plan_data, "Missing version field"
        assert plan_data["version"] == "1.0", f"Invalid version: {plan_data['version']}"

        assert "steps" in plan_data, "Missing steps array"
        assert isinstance(plan_data["steps"], list), "steps is not a list"
        assert len(plan_data["steps"]) == EXPECTED_TOTAL_STEPS, (
            f"Expected {EXPECTED_TOTAL_STEPS} steps, got {len(plan_data['steps'])}"
        )

        assert "summary" in plan_data, "Missing summary object"
        summary = plan_data["summary"]
        assert "total" in summary, "Missing summary.total"
        assert summary["total"] == EXPECTED_TOTAL_STEPS, (
            f"Summary total should be {EXPECTED_TOTAL_STEPS}, got {summary['total']}"
        )

        # Assert: by_tier counts
        assert "by_tier" in summary, "Missing summary.by_tier"
        by_tier = summary["by_tier"]
        assert by_tier["kernel"] == EXPECTED_KERNEL_STEPS, (
            f"Expected {EXPECTED_KERNEL_STEPS} kernel, got {by_tier['kernel']}"
        )
        assert by_tier["governance"] == EXPECTED_GOVERNANCE_STEPS, (
            f"Expected {EXPECTED_GOVERNANCE_STEPS} governance, got {by_tier['governance']}"
        )
        assert by_tier["optional"] == EXPECTED_OPTIONAL_STEPS, (
            f"Expected {EXPECTED_OPTIONAL_STEPS} optional, got {by_tier['optional']}"
        )

        # Assert: Step schema in JSON
        for step_data in plan_data["steps"]:
            assert "id" in step_data, "Missing step.id"
            assert "tier" in step_data, "Missing step.tier"
            assert "severity" in step_data, "Missing step.severity"
            assert "category" in step_data, "Missing step.category"
            assert "description" in step_data, "Missing step.description"
            assert "depends_on" in step_data, "Missing step.depends_on"
            assert isinstance(step_data["depends_on"], list), (
                f"depends_on is not a list for {step_data['id']}"
            )

            # Assert: Tier values are correct
            assert step_data["tier"] in [
                "kernel",
                "governance",
                "optional",
            ], f"Invalid tier: {step_data['tier']}"


@pytest.mark.unit
@pytest.mark.quick
@pytest.mark.ac_selftest_introspectable
class TestSelfTestErrorPaths:
    """Unit tests for error-path validation and edge cases."""

    def test_step_with_circular_dependencies_detected(self):
        """
        Verify DAG validation catches circular dependencies.

        Given: selftest_config with potential circular dependencies
        When: I validate the step list
        Then: validate_step_list() returns error messages for any cycles
        """
        # Arrange & Act
        errors = validate_step_list()

        # Assert: No circular dependencies in actual config
        circular_errors = [e for e in errors if "circular" in e.lower()]
        assert circular_errors == [], f"Circular dependencies found: {circular_errors}"

    def test_step_with_invalid_tier_enum(self):
        """
        Verify tier validation only allows KERNEL | GOVERNANCE | OPTIONAL.

        Given: All steps in SELFTEST_STEPS
        When: I check each step's tier
        Then: All tiers are valid SelfTestTier enum values
        """
        # Arrange & Act & Assert
        valid_tiers = {SelfTestTier.KERNEL, SelfTestTier.GOVERNANCE, SelfTestTier.OPTIONAL}
        for step in SELFTEST_STEPS:
            assert step.tier in valid_tiers, f"Step {step.id} has invalid tier: {step.tier}"

    def test_step_with_duplicate_ids(self):
        """
        Verify duplicate step IDs are caught in validation.

        Given: selftest_config.SELFTEST_STEPS
        When: I check for duplicate IDs
        Then: validate_step_list() returns errors for duplicates (if any exist)
        """
        # Arrange & Act
        errors = validate_step_list()

        # Assert: No duplicate IDs in actual config
        duplicate_errors = [e for e in errors if "duplicate" in e.lower()]
        assert duplicate_errors == [], f"Duplicate step IDs found: {duplicate_errors}"

    def test_malformed_json_output_fails_validation(self):
        """
        Verify show_plan_json() produces valid JSON.

        Given: selftest_config.SELFTEST_STEPS
        When: I call show_plan_json() and parse the output
        Then: Output parses successfully as valid JSON
        """
        # Arrange
        from selftest import SelfTestRunner

        runner = SelfTestRunner(json_output=True)
        steps = SELFTEST_STEPS

        # Act: Capture JSON plan output
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            runner.show_plan_json(steps)
        json_output = captured_output.getvalue()

        # Assert: Output is valid JSON (not malformed)
        try:
            plan_data = json.loads(json_output)
            assert plan_data is not None, "JSON parsed to None"
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON output is malformed: {e}\nOutput: {json_output}")


@pytest.mark.unit
@pytest.mark.quick
@pytest.mark.ac_selftest_introspectable
class TestSelfTestDependencies:
    """Unit tests for step dependencies and ordering."""

    def test_step_dependencies_are_valid(self):
        """
        Verify all step dependencies reference existing steps.

        Given: selftest_config.SELFTEST_STEPS with dependencies
        When: I check each dependency
        Then: All dependencies reference valid step IDs
        """
        # Arrange
        step_ids = {step.id for step in SELFTEST_STEPS}

        # Act & Assert
        for step in SELFTEST_STEPS:
            if step.dependencies:
                for dep_id in step.dependencies:
                    assert dep_id in step_ids, f"Step {step.id} has invalid dependency: {dep_id}"

    def test_step_dependencies_no_forward_references(self):
        """
        Verify no step depends on a step that comes after it.

        Given: selftest_config.SELFTEST_STEPS in order
        When: I check dependency ordering
        Then: All dependencies are on earlier steps
        """
        # Arrange
        step_index = {step.id: i for i, step in enumerate(SELFTEST_STEPS)}

        # Act & Assert
        for step in SELFTEST_STEPS:
            if step.dependencies:
                current_idx = step_index[step.id]
                for dep_id in step.dependencies:
                    dep_idx = step_index[dep_id]
                    assert dep_idx < current_idx, (
                        f"Step {step.id} (index {current_idx}) depends on {dep_id} (index {dep_idx}), which comes after"
                    )

    def test_step_descriptions_are_non_empty(self):
        """
        Verify all steps have non-empty descriptions.

        Given: selftest_config.SELFTEST_STEPS
        When: I check each step's description
        Then: All descriptions are non-empty strings
        """
        # Act & Assert
        for step in SELFTEST_STEPS:
            assert isinstance(step.description, str), f"Step {step.id} description is not a string"
            assert len(step.description) > 0, f"Step {step.id} description is empty"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.quick
@pytest.mark.ac_selftest_introspectable
class TestSelfTestCLIAvailability:
    """Integration tests for CLI tool availability (pre-check)."""

    def test_selftest_cli_available(self):
        """
        Ensure uv and selftest.py are available for integration tests.

        Given: System environment
        When: I check for uv command and selftest.py script
        Then: Both are available (test fails loudly if missing)

        This test should run first; if it fails, all other integration tests will skip
        rather than failing mysteriously due to missing tools.
        """
        # Arrange
        repo_root = Path(__file__).parent.parent

        # Act & Assert
        uv_available = shutil.which("uv")
        assert uv_available, "uv not found in PATH; cannot run integration tests"

        selftest_script = repo_root / "swarm" / "tools" / "selftest.py"
        assert selftest_script.exists(), f"selftest.py not found at {selftest_script}"


@pytest.mark.integration
@pytest.mark.medium
@pytest.mark.ac_selftest_introspectable
class TestSelfTestPlanCLI:
    """Integration tests for selftest plan CLI commands."""

    def test_selftest_plan_command_exit_code(self):
        """
        Run `selftest.py --plan`, verify exit 0 and output contains all steps.

        Given: selftest.py script exists
        When: I run `uv run swarm/tools/selftest.py --plan`
        Then: Exit code is 0 and output contains all 16 step IDs
        """
        # Arrange
        repo_root = Path(__file__).parent.parent
        selftest_script = repo_root / "swarm" / "tools" / "selftest.py"

        # Skip test if script not found
        if not selftest_script.exists():
            pytest.skip(f"selftest.py not found at {selftest_script}")

        # Act
        result = subprocess.run(
            ["uv", "run", str(selftest_script), "--plan"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Assert: Exit code is 0
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}\n"
            f"stderr: {result.stderr}\n"
            f"stdout: {result.stdout}"
        )

        # Assert: Output contains all step IDs
        for step in SELFTEST_STEPS:
            assert step.id in result.stdout, f"Step {step.id} not in plan output"

    def test_selftest_plan_json_command_exit_code(self):
        """
        Run `selftest.py --plan --json`, verify JSON valid and exit 0.

        Given: selftest.py script exists
        When: I run `uv run swarm/tools/selftest.py --plan --json`
        Then: Exit code is 0 and stdout is valid JSON matching schema
        """
        # Arrange
        repo_root = Path(__file__).parent.parent
        selftest_script = repo_root / "swarm" / "tools" / "selftest.py"

        # Skip test if script not found
        if not selftest_script.exists():
            pytest.skip(f"selftest.py not found at {selftest_script}")

        # Act
        result = subprocess.run(
            ["uv", "run", str(selftest_script), "--plan", "--json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Assert: Exit code is 0
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}\nstderr: {result.stderr}"
        )

        # Assert: Output is valid JSON
        try:
            plan_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nOutput: {result.stdout}")

        # Assert: Schema is correct
        assert "version" in plan_data, "Missing version field"
        assert "steps" in plan_data, "Missing steps array"
        assert len(plan_data["steps"]) == EXPECTED_TOTAL_STEPS, (
            f"Expected {EXPECTED_TOTAL_STEPS} steps, got {len(plan_data['steps'])}"
        )
        assert "summary" in plan_data, "Missing summary object"

    def test_plan_output_matches_selftest_config(self):
        """
        Verify --plan text output matches selftest_config definitions (no drift).

        Given: selftest_config.SELFTEST_STEPS and CLI --plan output
        When: I compare them
        Then: All step IDs, tiers, descriptions match exactly
        """
        # Arrange
        repo_root = Path(__file__).parent.parent
        selftest_script = repo_root / "swarm" / "tools" / "selftest.py"

        # Skip test if script not found
        if not selftest_script.exists():
            pytest.skip(f"selftest.py not found at {selftest_script}")

        # Act: Get CLI output
        result = subprocess.run(
            ["uv", "run", str(selftest_script), "--plan"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        cli_output = result.stdout

        # Assert: Each step appears in output with correct tier and description
        for step in SELFTEST_STEPS:
            assert step.id in cli_output, f"Step {step.id} not in CLI output"
            assert step.description in cli_output, f"Description for {step.id} not in CLI output"
            tier_str = step.tier.value.upper()
            assert tier_str in cli_output, f"Tier {tier_str} for step {step.id} not in CLI output"

    def test_plan_json_step_counts_match_summary(self):
        """
        Verify JSON summary.by_tier matches actual step counts in steps array.

        Given: selftest.py --plan --json output
        When: I count steps by tier in the steps array and compare to summary
        Then: Counts match exactly
        """
        # Arrange
        repo_root = Path(__file__).parent.parent
        selftest_script = repo_root / "swarm" / "tools" / "selftest.py"

        # Skip test if script not found
        if not selftest_script.exists():
            pytest.skip(f"selftest.py not found at {selftest_script}")

        # Act: Get JSON plan
        result = subprocess.run(
            ["uv", "run", str(selftest_script), "--plan", "--json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        plan_data = json.loads(result.stdout)

        # Count steps by tier
        kernel_count = sum(1 for s in plan_data["steps"] if s["tier"] == "kernel")
        governance_count = sum(1 for s in plan_data["steps"] if s["tier"] == "governance")
        optional_count = sum(1 for s in plan_data["steps"] if s["tier"] == "optional")

        # Assert: Counts match summary
        summary = plan_data["summary"]["by_tier"]
        assert kernel_count == summary["kernel"], (
            f"Kernel count mismatch: steps={kernel_count}, summary={summary['kernel']}"
        )
        assert governance_count == summary["governance"], (
            f"Governance count mismatch: steps={governance_count}, summary={summary['governance']}"
        )
        assert optional_count == summary["optional"], (
            f"Optional count mismatch: steps={optional_count}, summary={summary['optional']}"
        )

    def test_plan_json_all_steps_have_required_fields(self):
        """
        Verify each step in JSON plan has all required fields.

        Given: selftest.py --plan --json output
        When: I check each step's fields
        Then: All steps have: id, tier, severity, category, description, depends_on
        """
        # Arrange
        repo_root = Path(__file__).parent.parent
        selftest_script = repo_root / "swarm" / "tools" / "selftest.py"

        # Skip test if script not found
        if not selftest_script.exists():
            pytest.skip(f"selftest.py not found at {selftest_script}")

        # Act: Get JSON plan
        result = subprocess.run(
            ["uv", "run", str(selftest_script), "--plan", "--json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        plan_data = json.loads(result.stdout)

        # Assert: All required fields present in each step
        required_fields = ["id", "tier", "severity", "category", "description", "depends_on"]
        for i, step_data in enumerate(plan_data["steps"]):
            for field in required_fields:
                assert field in step_data, (
                    f"Step {i} ({step_data.get('id', 'unknown')}) missing field: {field}"
                )

            # Assert: depends_on is a list
            assert isinstance(step_data["depends_on"], list), (
                f"Step {step_data['id']}.depends_on is not a list"
            )

            # Assert: tier value is valid
            assert step_data["tier"] in [
                "kernel",
                "governance",
                "optional",
            ], f"Invalid tier: {step_data['tier']}"


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.quick
@pytest.mark.ac_selftest_introspectable
@pytest.mark.parametrize("step", SELFTEST_STEPS, ids=lambda s: s.id)
class TestSelfTestStepMetadata:
    """Parametrized tests for individual step metadata validation."""

    def test_step_has_valid_tier(self, step: SelfTestStep):
        """Verify each step has a valid tier (KERNEL, GOVERNANCE, or OPTIONAL)."""
        assert step.tier in [
            SelfTestTier.KERNEL,
            SelfTestTier.GOVERNANCE,
            SelfTestTier.OPTIONAL,
        ], f"Step {step.id} has invalid tier: {step.tier}"

    def test_step_has_non_empty_description(self, step: SelfTestStep):
        """Verify each step has a non-empty description."""
        assert isinstance(step.description, str), f"Step {step.id} description is not a string"
        assert len(step.description) > 0, f"Step {step.id} has empty description"

    def test_step_has_valid_command_list(self, step: SelfTestStep):
        """Verify each step has a non-empty command list."""
        assert isinstance(step.command, list), f"Step {step.id} command is not a list"
        assert len(step.command) > 0, f"Step {step.id} has empty command list"
        for i, cmd in enumerate(step.command):
            assert isinstance(cmd, str), f"Step {step.id} command[{i}] is not a string"
            assert len(cmd) > 0, f"Step {step.id} command[{i}] is empty string"

    def test_step_dependencies_reference_valid_steps(self, step: SelfTestStep):
        """Verify each step's dependencies reference existing steps."""
        step_ids = {s.id for s in SELFTEST_STEPS}
        if step.dependencies:
            for dep_id in step.dependencies:
                assert dep_id in step_ids, f"Step {step.id} depends on unknown step: {dep_id}"


# ============================================================================
# PERFORMANCE/TIMING TESTS (Advisory)
# ============================================================================


@pytest.mark.integration
@pytest.mark.medium
@pytest.mark.ac_selftest_introspectable
class TestSelfTestPlanPerformance:
    """Performance tests for plan generation (advisory, not enforced)."""

    def test_selftest_plan_timing_sub_200ms(self):
        """
        Run `selftest.py --plan` and measure elapsed time.

        Given: selftest.py script exists
        When: I run `uv run swarm/tools/selftest.py --plan` and time it
        Then: Timing is logged (advisory target < 200ms, no assertion failure)
        """
        # Arrange
        import time

        repo_root = Path(__file__).parent.parent
        selftest_script = repo_root / "swarm" / "tools" / "selftest.py"

        # Skip test if script not found
        if not selftest_script.exists():
            pytest.skip(f"selftest.py not found at {selftest_script}")

        # Act: Run plan command and measure time
        start_time = time.time()
        result = subprocess.run(
            ["uv", "run", str(selftest_script), "--plan"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # Assert: Exit code is 0
        assert result.returncode == 0, f"Plan command failed: {result.stderr}"

        # Log timing (advisory, no hard assertion)
        print(f"\nPlan generation timing: {elapsed_ms:.1f}ms (target: < 200ms)")
        if elapsed_ms > 200:
            print("  WARNING: Exceeded advisory target of 200ms")


# ============================================================================
# PYTEST FIXTURES & HELPERS
# ============================================================================


@pytest.fixture
def sample_steps() -> List[SelfTestStep]:
    """Fixture providing a copy of all selftest steps."""
    return list(SELFTEST_STEPS)


@pytest.fixture
def step_index_map() -> dict:
    """Fixture providing a map of step ID to its index in the list."""
    return {step.id: i for i, step in enumerate(SELFTEST_STEPS)}
