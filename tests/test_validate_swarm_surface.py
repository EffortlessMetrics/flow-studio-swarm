# tests/test_validate_swarm_surface.py
"""Surface tests for validate_swarm modularization.

These tests ensure backward compatibility during and after the modularization
of validate_swarm.py into swarm/tools/validation/.

The key invariants:
1. Legacy imports from validate_swarm.py still work (shim)
2. Modular imports from swarm.tools.validation work
3. CLI behavior is preserved (exit codes, flags, output formats)
"""

import subprocess
import sys
from pathlib import Path


class TestLegacyImports:
    """Test that legacy imports still work through the shim."""

    def test_main_importable_from_shim(self):
        """The shim file should export main()."""
        # Import through the shim path
        import swarm.tools.validate_swarm as shim
        assert hasattr(shim, 'main')
        assert callable(shim.main)


class TestModularImports:
    """Test that modular imports work correctly."""

    def test_public_api_exports(self):
        """The validation package should export its public API."""
        from swarm.tools.validation import (
            main,
            run_validation,
            ValidatorRunner,
            parse_agents_registry,
        )
        assert callable(main)
        assert callable(run_validation)
        assert callable(parse_agents_registry)
        # ValidatorRunner is a class
        assert isinstance(ValidatorRunner, type)

    def test_constants_importable(self):
        """Constants should be importable."""
        from swarm.tools.validation.constants import (
            BUILT_IN_AGENTS,
            VALID_MODELS,
            VALID_COLORS,
            ROLE_FAMILY_COLOR_MAP,
            EXIT_SUCCESS,
            EXIT_VALIDATION_FAILED,
            EXIT_FATAL_ERROR,
        )
        assert isinstance(BUILT_IN_AGENTS, list)
        assert isinstance(VALID_MODELS, list)
        assert isinstance(VALID_COLORS, list)
        assert isinstance(ROLE_FAMILY_COLOR_MAP, dict)
        assert EXIT_SUCCESS == 0
        assert EXIT_VALIDATION_FAILED == 1
        assert EXIT_FATAL_ERROR == 2

    def test_helpers_importable(self):
        """Helpers should be importable."""
        from swarm.tools.validation.helpers import (
            safe_get_stripped,
            find_repo_root,
            ROOT,
            AGENTS_MD,
            FLOW_SPECS_DIR,
            FLOWS_CONFIG_DIR,
            AGENTS_DIR,
            SKILLS_DIR,
        )
        assert callable(safe_get_stripped)
        assert callable(find_repo_root)
        assert isinstance(ROOT, Path)
        assert isinstance(AGENTS_MD, Path)

    def test_registry_importable(self):
        """Registry functions should be importable."""
        from swarm.tools.validation.registry import (
            parse_agents_registry,
            parse_config_files,
        )
        assert callable(parse_agents_registry)
        assert callable(parse_config_files)

    def test_git_helpers_importable(self):
        """Git helpers should be importable."""
        from swarm.tools.validation.git_helpers import (
            get_modified_files,
            should_check_file,
        )
        assert callable(get_modified_files)
        assert callable(should_check_file)

    def test_validators_importable(self):
        """All validators should be importable."""
        from swarm.tools.validation.validators import (
            validate_bijection,
            validate_frontmatter,
            validate_colors,
            validate_config_coverage,
            validate_flow_references,
            validate_skills,
            validate_runbase_paths,
            validate_prompt_sections,
            validate_microloop_phrases,
            validate_capability_registry,
        )
        # All should be callable
        for fn in [
            validate_bijection,
            validate_frontmatter,
            validate_colors,
            validate_config_coverage,
            validate_flow_references,
            validate_skills,
            validate_runbase_paths,
            validate_prompt_sections,
            validate_microloop_phrases,
            validate_capability_registry,
        ]:
            assert callable(fn)

    def test_flow_validators_importable(self):
        """Flow validators should be importable."""
        from swarm.tools.validation.validators.flows import (
            parse_flow_config,
            validate_no_empty_flows,
            validate_no_agentless_steps,
            validate_flow_agent_validity,
            validate_flow_documentation_completeness,
            validate_flow_studio_sync,
            validate_utility_flow_graphs,
        )
        for fn in [
            parse_flow_config,
            validate_no_empty_flows,
            validate_no_agentless_steps,
            validate_flow_agent_validity,
            validate_flow_documentation_completeness,
            validate_flow_studio_sync,
            validate_utility_flow_graphs,
        ]:
            assert callable(fn)

    def test_reporting_importable(self):
        """Reporting functions should be importable."""
        from swarm.tools.validation.reporting import (
            build_report_json,
            build_report_markdown,
            print_success,
            print_errors,
            print_json_output,
        )
        for fn in [
            build_report_json,
            build_report_markdown,
            print_success,
            print_errors,
            print_json_output,
        ]:
            assert callable(fn)

    def test_runner_importable(self):
        """Runner should be importable."""
        from swarm.tools.validation.runner import (
            ValidatorRunner,
            run_validation,
        )
        assert isinstance(ValidatorRunner, type)
        assert callable(run_validation)


class TestCLIBehavior:
    """Test CLI behavior is preserved."""

    def test_version_flag(self):
        """--version should return version info."""
        result = subprocess.run(
            [sys.executable, "swarm/tools/validate_swarm.py", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "2.1.0" in result.stdout

    def test_help_flag(self):
        """--help should show usage info."""
        result = subprocess.run(
            [sys.executable, "swarm/tools/validate_swarm.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Swarm alignment validator" in result.stdout
        assert "--strict" in result.stdout
        assert "--debug" in result.stdout
        assert "--json" in result.stdout

    def test_flows_only_runs(self):
        """--flows-only should run without errors."""
        result = subprocess.run(
            [sys.executable, "swarm/tools/validate_swarm.py", "--flows-only"],
            capture_output=True,
            text=True,
        )
        # Should either pass (0) or fail validation (1), not crash (2)
        assert result.returncode in [0, 1]


class TestFunctionalValidation:
    """Test that validation actually works."""

    def test_run_validation_returns_result(self):
        """run_validation should return a ValidationResult."""
        from swarm.tools.validation import run_validation
        from swarm.validator import ValidationResult

        result = run_validation(flows_only=True)
        assert isinstance(result, ValidationResult)

    def test_parse_agents_registry_returns_dict(self):
        """parse_agents_registry should return agent dict."""
        from swarm.tools.validation import parse_agents_registry

        registry = parse_agents_registry()
        assert isinstance(registry, dict)
        assert len(registry) > 0  # Should have agents

    def test_validator_runner_runs_all(self):
        """ValidatorRunner should run all checks."""
        from swarm.tools.validation import ValidatorRunner, parse_agents_registry
        from swarm.validator import ValidationResult

        registry = parse_agents_registry()
        runner = ValidatorRunner(registry, flows_only=True)
        result = runner.run_all()
        assert isinstance(result, ValidationResult)
