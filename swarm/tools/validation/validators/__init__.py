# swarm/tools/validation/validators/__init__.py
"""Validation functions for swarm alignment checks.

This module provides modular validators for the swarm validation system.
Each validator corresponds to one or more FR (Functional Requirement) rules:

- FR-001: Bijection (validate_bijection)
- FR-002: Frontmatter (validate_frontmatter)
- FR-002b: Colors (validate_colors)
- FR-003: Flow References (validate_flow_references)
- FR-004: Skills (validate_skills)
- FR-005: RUN_BASE Paths (validate_runbase_paths)
- FR-006: Prompt Sections (validate_prompt_sections)
- FR-007: Capability Registry (validate_capability_registry)
- FR-CONF-001: Config Coverage (validate_config_coverage)
"""

from swarm.tools.validation.validators.bijection import validate_bijection
from swarm.tools.validation.validators.frontmatter import validate_frontmatter
from swarm.tools.validation.validators.colors import validate_colors
from swarm.tools.validation.validators.config_coverage import (
    validate_config_coverage,
    parse_config_files,
)
from swarm.tools.validation.validators.flow_references import (
    levenshtein_distance,
    suggest_typos,
    parse_flow_spec_agents,
    validate_flow_references,
)
from swarm.tools.validation.validators.skills import validate_skills
from swarm.tools.validation.validators.runbase import validate_runbase_paths
from swarm.tools.validation.validators.prompts import validate_prompt_sections
from swarm.tools.validation.validators.microloops import validate_microloop_phrases
from swarm.tools.validation.validators.capabilities import validate_capability_registry

__all__ = [
    # bijection.py (FR-001)
    "validate_bijection",
    # frontmatter.py (FR-002)
    "validate_frontmatter",
    # colors.py (FR-002b)
    "validate_colors",
    # config_coverage.py (FR-CONF-001)
    "validate_config_coverage",
    "parse_config_files",
    # flow_references.py (FR-003)
    "levenshtein_distance",
    "suggest_typos",
    "parse_flow_spec_agents",
    "validate_flow_references",
    # skills.py (FR-004)
    "validate_skills",
    # runbase.py (FR-005)
    "validate_runbase_paths",
    # prompts.py (FR-006)
    "validate_prompt_sections",
    # microloops.py
    "validate_microloop_phrases",
    # capabilities.py (FR-007)
    "validate_capability_registry",
]
