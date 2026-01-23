"""Tests for configuration handling."""

import tempfile

import pytest

from selftest_core import (
    Category,
    Severity,
    Tier,
    load_config,
    load_steps_from_list,
    load_steps_from_yaml,
    step_from_dict,
    validate_steps,
)
from selftest_core.config import SelftestConfig


class TestStepFromDict:
    """Tests for step_from_dict function."""

    def test_basic_step(self):
        """Test creating step from basic dict."""
        data = {
            "id": "test",
            "tier": "kernel",
            "command": "echo hello",
        }
        step = step_from_dict(data)
        assert step.id == "test"
        assert step.tier == Tier.KERNEL
        assert step.command == "echo hello"

    def test_full_step(self):
        """Test creating step with all fields."""
        data = {
            "id": "full",
            "tier": "governance",
            "command": "pytest",
            "description": "Run tests",
            "severity": "critical",
            "category": "correctness",
            "timeout": 120,
            "dependencies": ["lint"],
            "allow_fail_in_degraded": True,
        }
        step = step_from_dict(data)
        assert step.id == "full"
        assert step.tier == Tier.GOVERNANCE
        assert step.command == "pytest"
        assert step.description == "Run tests"
        assert step.severity == Severity.CRITICAL
        assert step.category == Category.CORRECTNESS
        assert step.timeout == 120
        assert step.dependencies == ["lint"]
        assert step.allow_fail_in_degraded is True

    def test_command_list(self):
        """Test that command list is joined."""
        data = {
            "id": "multi",
            "tier": "kernel",
            "command": ["cmd1", "cmd2", "cmd3"],
        }
        step = step_from_dict(data)
        assert step.command == "cmd1 && cmd2 && cmd3"

    def test_missing_id(self):
        """Test error on missing id."""
        with pytest.raises(ValueError, match="must have an 'id' field"):
            step_from_dict({"tier": "kernel", "command": "true"})

    def test_missing_command(self):
        """Test error on missing command."""
        with pytest.raises(ValueError, match="must have a 'command' field"):
            step_from_dict({"id": "test", "tier": "kernel"})

    def test_missing_tier(self):
        """Test error on missing tier."""
        with pytest.raises(ValueError, match="must have a 'tier' field"):
            step_from_dict({"id": "test", "command": "true"})

    def test_invalid_tier(self):
        """Test error on invalid tier."""
        with pytest.raises(ValueError, match="Invalid tier"):
            step_from_dict({"id": "test", "tier": "invalid", "command": "true"})

    def test_invalid_severity(self):
        """Test error on invalid severity."""
        with pytest.raises(ValueError, match="Invalid severity"):
            step_from_dict(
                {
                    "id": "test",
                    "tier": "kernel",
                    "command": "true",
                    "severity": "invalid",
                }
            )

    def test_invalid_category(self):
        """Test error on invalid category."""
        with pytest.raises(ValueError, match="Invalid category"):
            step_from_dict(
                {
                    "id": "test",
                    "tier": "kernel",
                    "command": "true",
                    "category": "invalid",
                }
            )


class TestLoadStepsFromYaml:
    """Tests for loading steps from YAML files."""

    def test_load_basic_yaml(self):
        """Test loading basic YAML config."""
        yaml_content = """
steps:
  - id: lint
    tier: kernel
    command: ruff check .
    description: Python linting

  - id: test
    tier: kernel
    command: pytest
    description: Unit tests
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            steps = load_steps_from_yaml(f.name)

        assert len(steps) == 2
        assert steps[0].id == "lint"
        assert steps[1].id == "test"

    def test_file_not_found(self):
        """Test error on missing file."""
        with pytest.raises(FileNotFoundError):
            load_steps_from_yaml("/nonexistent/file.yaml")

    def test_empty_yaml(self):
        """Test error on empty YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            with pytest.raises(ValueError, match="Empty or invalid"):
                load_steps_from_yaml(f.name)

    def test_missing_steps_key(self):
        """Test error when steps key is missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("other_key: value\n")
            f.flush()
            with pytest.raises(ValueError, match="must have a 'steps' key"):
                load_steps_from_yaml(f.name)


class TestLoadStepsFromList:
    """Tests for loading steps from list."""

    def test_load_list(self):
        """Test loading from list of dicts."""
        data = [
            {"id": "a", "tier": "kernel", "command": "true"},
            {"id": "b", "tier": "governance", "command": "true"},
        ]
        steps = load_steps_from_list(data)
        assert len(steps) == 2
        assert steps[0].id == "a"
        assert steps[1].id == "b"


class TestValidateSteps:
    """Tests for step validation."""

    def test_valid_steps(self):
        """Test validation passes for valid steps."""
        data = [
            {"id": "a", "tier": "kernel", "command": "true"},
            {"id": "b", "tier": "kernel", "command": "true", "dependencies": ["a"]},
        ]
        steps = load_steps_from_list(data)
        errors = validate_steps(steps)
        assert errors == []

    def test_duplicate_ids(self):
        """Test detection of duplicate IDs."""
        data = [
            {"id": "dup", "tier": "kernel", "command": "true"},
            {"id": "dup", "tier": "kernel", "command": "true"},
        ]
        steps = load_steps_from_list(data)
        errors = validate_steps(steps)
        assert any("Duplicate" in e for e in errors)

    def test_invalid_dependency(self):
        """Test detection of invalid dependencies."""
        data = [
            {
                "id": "a",
                "tier": "kernel",
                "command": "true",
                "dependencies": ["nonexistent"],
            },
        ]
        steps = load_steps_from_list(data)
        errors = validate_steps(steps)
        assert any("invalid dependency" in e for e in errors)

    def test_circular_dependency(self):
        """Test detection of circular dependencies."""
        data = [
            {"id": "a", "tier": "kernel", "command": "true", "dependencies": ["b"]},
            {"id": "b", "tier": "kernel", "command": "true", "dependencies": ["a"]},
        ]
        steps = load_steps_from_list(data)
        errors = validate_steps(steps)
        assert any("Circular" in e for e in errors)


class TestSelftestConfig:
    """Tests for SelftestConfig class."""

    def test_from_yaml(self):
        """Test loading config from YAML."""
        yaml_content = """
mode: degraded
verbose: true
write_report: false
steps:
  - id: test
    tier: kernel
    command: pytest
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = SelftestConfig.from_yaml(f.name)

        assert config.mode == "degraded"
        assert config.verbose is True
        assert config.write_report is False
        assert len(config.steps) == 1

    def test_from_dict(self):
        """Test loading config from dict."""
        data = {
            "mode": "kernel-only",
            "steps": [
                {"id": "a", "tier": "kernel", "command": "true"},
            ],
        }
        config = SelftestConfig.from_dict(data)
        assert config.mode == "kernel-only"
        assert len(config.steps) == 1


class TestLoadConfig:
    """Tests for load_config convenience function."""

    def test_load_from_dict(self):
        """Test loading from dict."""
        data = {
            "steps": [{"id": "a", "tier": "kernel", "command": "true"}],
        }
        config = load_config(data)
        assert len(config.steps) == 1

    def test_load_from_path(self):
        """Test loading from path."""
        yaml_content = """
steps:
  - id: test
    tier: kernel
    command: pytest
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_config(f.name)

        assert len(config.steps) == 1
