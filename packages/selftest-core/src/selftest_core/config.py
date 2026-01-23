"""
Configuration handling for selftest.

This module provides utilities for loading step definitions from various
sources including YAML files, Python modules, and dictionaries.

Example YAML configuration:
    steps:
      - id: lint
        tier: kernel
        command: ruff check .
        description: Python linting
        severity: critical
        category: correctness

      - id: test
        tier: kernel
        command: pytest tests/
        description: Unit tests
        dependencies:
          - lint

Example usage:
    from selftest_core.config import load_config, load_steps_from_yaml

    # Load from YAML file
    steps = load_steps_from_yaml(Path("selftest.yaml"))

    # Load from config dict
    config = load_config({
        "steps": [...],
        "mode": "strict",
    })
"""

from pathlib import Path
from typing import Any

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader  # type: ignore[assignment]

from .runner import Category, Severity, Step, Tier


def _parse_tier(value: str) -> Tier:
    """Parse tier string to Tier enum."""
    value = value.lower()
    if value == "kernel":
        return Tier.KERNEL
    elif value == "governance":
        return Tier.GOVERNANCE
    elif value == "optional":
        return Tier.OPTIONAL
    else:
        raise ValueError(
            f"Invalid tier: {value}. Must be kernel, governance, or optional."
        )


def _parse_severity(value: str) -> Severity:
    """Parse severity string to Severity enum."""
    value = value.lower()
    if value == "critical":
        return Severity.CRITICAL
    elif value == "warning":
        return Severity.WARNING
    elif value == "info":
        return Severity.INFO
    else:
        raise ValueError(
            f"Invalid severity: {value}. Must be critical, warning, or info."
        )


def _parse_category(value: str) -> Category:
    """Parse category string to Category enum."""
    value = value.lower()
    if value == "security":
        return Category.SECURITY
    elif value == "performance":
        return Category.PERFORMANCE
    elif value == "correctness":
        return Category.CORRECTNESS
    elif value == "governance":
        return Category.GOVERNANCE
    else:
        raise ValueError(
            f"Invalid category: {value}. "
            "Must be security, performance, correctness, or governance."
        )


def step_from_dict(data: dict[str, Any]) -> Step:
    """
    Create a Step from a dictionary.

    Args:
        data: Dictionary with step configuration

    Returns:
        Step object

    Raises:
        ValueError: If required fields are missing or invalid
    """
    if "id" not in data:
        raise ValueError("Step must have an 'id' field")
    if "command" not in data:
        raise ValueError("Step must have a 'command' field")
    if "tier" not in data:
        raise ValueError("Step must have a 'tier' field")

    # Handle command as string or list
    command = data["command"]
    if isinstance(command, list):
        command = " && ".join(command)

    return Step(
        id=data["id"],
        tier=_parse_tier(data["tier"]),
        command=command,
        description=data.get("description", ""),
        severity=_parse_severity(data.get("severity", "warning")),
        category=_parse_category(data.get("category", "correctness")),
        timeout=data.get("timeout", 60),
        dependencies=data.get("dependencies", []),
        allow_fail_in_degraded=data.get("allow_fail_in_degraded", False),
    )


def load_steps_from_yaml(path: str | Path) -> list[Step]:
    """
    Load step definitions from a YAML file.

    The YAML file should have a top-level 'steps' key containing a list
    of step definitions.

    Args:
        path: Path to the YAML file

    Returns:
        List of Step objects

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the YAML is invalid or missing required fields
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        data = yaml.load(f, Loader=SafeLoader)

    if data is None:
        raise ValueError(f"Empty or invalid YAML file: {path}")

    if "steps" not in data:
        raise ValueError(f"YAML file must have a 'steps' key: {path}")

    steps = []
    for i, step_data in enumerate(data["steps"]):
        try:
            steps.append(step_from_dict(step_data))
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid step at index {i}: {e}") from e

    return steps


def load_steps_from_list(steps_data: list[dict[str, Any]]) -> list[Step]:
    """
    Load steps from a list of dictionaries.

    Args:
        steps_data: List of step configuration dictionaries

    Returns:
        List of Step objects
    """
    return [step_from_dict(data) for data in steps_data]


class SelftestConfig:
    """
    Configuration container for selftest execution.

    Holds step definitions and execution settings.

    Attributes:
        steps: List of Step objects to execute
        mode: Execution mode ('strict', 'degraded', 'kernel-only')
        verbose: Enable verbose output
        write_report: Write JSON report after execution
        report_path: Path for JSON report (default: selftest_report.json)
    """

    def __init__(
        self,
        steps: list[Step],
        mode: str = "strict",
        verbose: bool = False,
        write_report: bool = True,
        report_path: str | None = None,
    ):
        self.steps = steps
        self.mode = mode
        self.verbose = verbose
        self.write_report = write_report
        self.report_path = report_path or "selftest_report.json"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SelftestConfig":
        """
        Load configuration from a YAML file.

        The YAML can include both step definitions and execution settings:

            mode: strict
            verbose: false
            write_report: true
            report_path: ./reports/selftest.json
            steps:
              - id: lint
                tier: kernel
                command: ruff check .

        Args:
            path: Path to YAML configuration file

        Returns:
            SelftestConfig instance
        """
        path = Path(path)
        with open(path) as f:
            data = yaml.load(f, Loader=SafeLoader)

        if data is None:
            raise ValueError(f"Empty or invalid YAML file: {path}")

        steps = load_steps_from_list(data.get("steps", []))

        return cls(
            steps=steps,
            mode=data.get("mode", "strict"),
            verbose=data.get("verbose", False),
            write_report=data.get("write_report", True),
            report_path=data.get("report_path"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SelftestConfig":
        """
        Create configuration from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            SelftestConfig instance
        """
        steps = load_steps_from_list(data.get("steps", []))

        return cls(
            steps=steps,
            mode=data.get("mode", "strict"),
            verbose=data.get("verbose", False),
            write_report=data.get("write_report", True),
            report_path=data.get("report_path"),
        )


def validate_steps(steps: list[Step]) -> list[str]:
    """
    Validate a list of steps for consistency.

    Checks for:
    - Duplicate step IDs
    - Invalid dependencies (referencing non-existent steps)
    - Circular dependencies

    Args:
        steps: List of steps to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    step_ids = {step.id for step in steps}

    # Check for duplicate IDs
    seen = set()
    for step in steps:
        if step.id in seen:
            errors.append(f"Duplicate step id: {step.id}")
        seen.add(step.id)

    # Check for invalid dependencies
    for step in steps:
        for dep_id in step.dependencies:
            if dep_id not in step_ids:
                errors.append(f"Step '{step.id}' has invalid dependency '{dep_id}'")

    # Check for circular dependencies
    def has_cycle(step_id: str, visited: set, rec_stack: set) -> bool:
        visited.add(step_id)
        rec_stack.add(step_id)

        step = next((s for s in steps if s.id == step_id), None)
        if step:
            for dep_id in step.dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id, visited, rec_stack):
                        return True
                elif dep_id in rec_stack:
                    return True

        rec_stack.remove(step_id)
        return False

    visited: set = set()
    for step in steps:
        if step.id not in visited:
            if has_cycle(step.id, visited, set()):
                errors.append(f"Circular dependency detected involving '{step.id}'")

    return errors


def load_config(source: str | Path | dict[str, Any]) -> SelftestConfig:
    """
    Load configuration from various sources.

    Convenience function that accepts:
    - Path to YAML file (str or Path)
    - Configuration dictionary

    Args:
        source: Configuration source

    Returns:
        SelftestConfig instance
    """
    if isinstance(source, dict):
        return SelftestConfig.from_dict(source)
    else:
        return SelftestConfig.from_yaml(source)
