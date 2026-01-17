# swarm/tools/validation/__init__.py
"""Swarm validation library - modular validation for swarm alignment.

This package provides validation for swarm spec/implementation alignment.

Public API:
- run_validation(): Main validation entry point
- ValidatorRunner: Class for running validation checks
- parse_agents_registry(): Parse AGENTS.md registry
- main(): CLI entry point

For individual validators, import from swarm.tools.validation.validators.
"""

from .cli import main
from .git_helpers import get_modified_files, should_check_file
from .registry import parse_agents_registry, parse_config_files, _parse_raw_yaml
from .runner import ValidatorRunner, run_validation

__all__ = [
    "main",
    "run_validation",
    "ValidatorRunner",
    "parse_agents_registry",
    "parse_config_files",
    "get_modified_files",
    "should_check_file",
    "_parse_raw_yaml",
]
