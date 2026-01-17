# swarm/tools/validation/runner.py
"""ValidatorRunner class and run_validation function.

This module provides the orchestration layer for running validation checks.
ValidatorRunner encapsulates the logic for running different categories of
validation (agents, flows, skills) with support for incremental mode and debug output.
"""

import sys
import time
from typing import Any, Dict, Optional, Set

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import FLOWS_CONFIG_DIR
from swarm.tools.validation.constants import EXIT_FATAL_ERROR
from swarm.tools.validation.git_helpers import get_modified_files
from swarm.tools.validation.registry import parse_agents_registry
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
from swarm.tools.validation.validators.flows import (
    parse_flow_config,
    validate_no_empty_flows,
    validate_no_agentless_steps,
    validate_flow_agent_validity,
    validate_flow_documentation_completeness,
    validate_flow_studio_sync,
    validate_utility_flow_graphs,
)


class ValidatorRunner:
    """
    Orchestrates validation checks for the swarm.

    Encapsulates the logic for running different categories of validation
    (agents, flows, skills) with support for incremental mode and debug output.

    Attributes:
        registry: Agent registry from AGENTS.md
        modified_files: Set of modified files (None = check all)
        debug: If True, print debug information
        strict: If True, enforce swarm design constraints as errors
        flows_only: If True, only run flow validation checks
        check_prompts: If True, validate agent prompt sections
    """

    def __init__(
        self,
        registry: Dict[str, Dict[str, Any]],
        modified_files: Optional[Set[str]] = None,
        debug: bool = False,
        strict: bool = False,
        flows_only: bool = False,
        check_prompts: bool = False,
    ):
        """
        Initialize the validator runner.

        Args:
            registry: Agent registry from AGENTS.md
            modified_files: Set of modified files for incremental mode (None = check all)
            debug: If True, print debug information to stderr
            strict: If True, enforce swarm design constraints as errors
            flows_only: If True, only run flow validation checks
            check_prompts: If True, validate agent prompt sections
        """
        self.registry = registry
        self.modified_files = modified_files
        self.debug = debug
        self.strict = strict
        self.flows_only = flows_only
        self.check_prompts = check_prompts

    def _should_check(self, *path_prefixes: str) -> bool:
        """
        Check if any file matching the given prefixes should be validated.

        Args:
            path_prefixes: Path prefixes to check (e.g., "swarm/AGENTS.md", ".claude/agents/")

        Returns:
            True if validation should run for these paths
        """
        if self.modified_files is None:
            return True
        return any(
            any(f.startswith(prefix) for prefix in path_prefixes)
            for f in self.modified_files
        )

    def _debug_print(self, message: str) -> None:
        """Print debug message to stderr if debug mode is enabled."""
        if self.debug:
            print(f"Debug: {message}", file=sys.stderr)

    def run_all(self) -> ValidationResult:
        """
        Run all validation checks.

        Returns:
            ValidationResult with all errors and warnings
        """
        start_time = time.time()
        result = ValidationResult()

        self._debug_print(f"Parsed {len(self.registry)} agents from registry")

        if self.flows_only:
            self._debug_print("Running flows-only validation")
            result.extend(self.run_flows())
        else:
            # Full validation: run all checks in order
            result.extend(self.run_agents())
            result.extend(self.run_flows())
            result.extend(self.run_skills())
            result.extend(self._run_microloop_validation())
            result.extend(self._run_prompt_validation())
            result.extend(self._run_capability_validation())

        elapsed = time.time() - start_time
        mode = "Flows-only" if self.flows_only else "Full"
        self._debug_print(f"{mode} validation completed in {elapsed:.3f}s")

        return result

    def run_agents(self) -> ValidationResult:
        """
        Run agent-related validation checks.

        Includes:
        - FR-CONF-001: Config coverage validation (new architecture)
        - FR-001: Bijection validation (LEGACY: skipped if .claude/agents/ doesn't exist)
        - FR-002: Frontmatter validation (LEGACY: skipped if .claude/agents/ doesn't exist)
        - FR-002b: Color validation (LEGACY: skipped if .claude/agents/ doesn't exist)

        Returns:
            ValidationResult with agent-related errors and warnings
        """
        result = ValidationResult()

        # FR-CONF-001: Config coverage validation
        if self._should_check("swarm/AGENTS.md", "swarm/config/agents/"):
            config_result = validate_config_coverage(self.registry)
            result.extend(config_result)
            self._debug_print(f"Config coverage check: {len(config_result.errors)} errors")

        # FR-001: Bijection validation
        if self._should_check("swarm/AGENTS.md", ".claude/agents/"):
            bijection_result = validate_bijection(self.registry)
            result.extend(bijection_result)
            self._debug_print(f"Bijection check: {len(bijection_result.errors)} errors")

        # FR-002: Frontmatter validation
        if self._should_check(".claude/agents/"):
            frontmatter_result = validate_frontmatter(self.registry, strict_mode=self.strict)
            result.extend(frontmatter_result)
            self._debug_print(
                f"Frontmatter check: {len(frontmatter_result.errors)} errors, "
                f"{len(frontmatter_result.warnings)} warnings"
            )

        # FR-002b: Color validation
        if self._should_check(".claude/agents/", "swarm/AGENTS.md"):
            color_result = validate_colors(self.registry)
            result.extend(color_result)
            self._debug_print(f"Color check: {len(color_result.errors)} errors")

        return result

    def run_flows(self) -> ValidationResult:
        """
        Run flow-related validation checks.

        Includes:
        - FR-003: Flow reference validation
        - FR-005: RUN_BASE validation
        - FR-FLOWS: Flow invariant checks (no empty flows, no agentless steps, etc.)

        Returns:
            ValidationResult with flow-related errors and warnings
        """
        result = ValidationResult()

        # FR-003: Flow reference validation (only in full mode, not flows_only)
        if not self.flows_only and self._should_check("swarm/flows/", "swarm/AGENTS.md"):
            reference_result = validate_flow_references(self.registry)
            result.extend(reference_result)
            self._debug_print(f"Reference check: {len(reference_result.errors)} errors")

        # FR-005: RUN_BASE validation (only in full mode, not flows_only)
        if not self.flows_only and self._should_check("swarm/flows/"):
            runbase_result = validate_runbase_paths()
            result.extend(runbase_result)
            self._debug_print(f"RUN_BASE check: {len(runbase_result.errors)} errors")

        # FR-FLOWS: Flow invariant checks
        if self.flows_only or self._should_check("swarm/config/flows/", "swarm/flows/"):
            result.extend(self._run_flow_invariant_checks())

        return result

    def _run_flow_invariant_checks(self) -> ValidationResult:
        """
        Run flow invariant validation checks.

        Parses flow configs and validates:
        - No empty flows
        - No agentless steps
        - Agent validity
        - Documentation completeness
        - Flow Studio sync (optional)
        - Utility flow consistency (FR-UTILITY)

        Returns:
            ValidationResult with flow invariant errors and warnings
        """
        result = ValidationResult()

        # Parse all flow configs
        flow_configs: Dict[str, Dict[str, Any]] = {}
        if FLOWS_CONFIG_DIR.is_dir():
            for flow_file in sorted(FLOWS_CONFIG_DIR.glob("*.yaml")):
                flow_id = flow_file.stem
                flow_configs[flow_id] = parse_flow_config(flow_file)
            self._debug_print(f"Parsed {len(flow_configs)} flow configs")

        # Invariant 1: No empty flows
        no_empty_result = validate_no_empty_flows(flow_configs)
        result.extend(no_empty_result)
        self._debug_print(f"No-empty-flows check: {len(no_empty_result.errors)} errors")

        # Invariant 2: No agentless steps
        no_agentless_result = validate_no_agentless_steps(flow_configs)
        result.extend(no_agentless_result)
        self._debug_print(f"No-agentless-steps check: {len(no_agentless_result.errors)} errors")

        # Invariant 3: Agent validity
        agent_validity_result = validate_flow_agent_validity(flow_configs, self.registry)
        result.extend(agent_validity_result)
        self._debug_print(f"Agent-validity check: {len(agent_validity_result.errors)} errors")

        # Invariant 4: Documentation completeness
        doc_completeness_result = validate_flow_documentation_completeness()
        result.extend(doc_completeness_result)
        self._debug_print(f"Doc-completeness check: {len(doc_completeness_result.errors)} errors")

        # Invariant 5: Flow Studio sync (optional)
        flow_studio_result = validate_flow_studio_sync()
        result.extend(flow_studio_result)
        self._debug_print(f"Flow-studio-sync check: {len(flow_studio_result.warnings)} warnings")

        # Invariant 6: Utility flow validation (flow graph JSON files)
        utility_flow_result = validate_utility_flow_graphs()
        result.extend(utility_flow_result)
        self._debug_print(f"Utility-flow check: {len(utility_flow_result.errors)} errors, {len(utility_flow_result.warnings)} warnings")

        return result

    def run_skills(self) -> ValidationResult:
        """
        Run skill-related validation checks.

        Includes:
        - FR-004: Skill validation

        Returns:
            ValidationResult with skill-related errors and warnings
        """
        result = ValidationResult()

        # FR-004: Skill validation
        if self._should_check(".claude/skills/", ".claude/agents/"):
            skill_result = validate_skills()
            result.extend(skill_result)
            self._debug_print(f"Skill check: {len(skill_result.errors)} errors")

        return result

    def _run_microloop_validation(self) -> ValidationResult:
        """
        Run microloop phrase validation.

        Includes:
        - FR-006a: Microloop phrase validation (ban old "restates concerns" patterns)

        Returns:
            ValidationResult with microloop-related errors
        """
        result = ValidationResult()

        # FR-006a: Microloop phrase validation
        if self._should_check(
            ".claude/commands/",
            "swarm/flows/",
            ".claude/agents/",
            "CLAUDE.md"
        ):
            microloop_result = validate_microloop_phrases()
            result.extend(microloop_result)
            self._debug_print(f"Microloop phrase check: {len(microloop_result.errors)} errors")

        return result

    def _run_prompt_validation(self) -> ValidationResult:
        """
        Run prompt section validation (optional).

        Includes:
        - FR-006b: Agent prompt section validation

        Returns:
            ValidationResult with prompt-related errors or warnings
        """
        result = ValidationResult()

        # FR-006b: Agent prompt section validation (optional, enabled with check_prompts)
        if self.check_prompts:
            if self._should_check(".claude/agents/"):
                prompt_result = validate_prompt_sections(self.registry, strict_mode=self.strict)
                result.extend(prompt_result)
                self._debug_print(
                    f"Prompt sections check: {len(prompt_result.errors)} errors, "
                    f"{len(prompt_result.warnings)} warnings"
                )

        return result

    def _run_capability_validation(self) -> ValidationResult:
        """
        Run capability registry validation.

        Includes:
        - FR-007: Capability registry validation

        Returns:
            ValidationResult with capability-related errors or warnings
        """
        result = ValidationResult()

        # FR-007: Capability registry validation
        if self._should_check("specs/capabilities.yaml", "features/"):
            capability_result = validate_capability_registry()
            result.extend(capability_result)
            self._debug_print(
                f"Capability registry check: {len(capability_result.errors)} errors, "
                f"{len(capability_result.warnings)} warnings"
            )

        return result


# ============================================================================
# Main Validation Orchestrator (Thin Wrapper)
# ============================================================================


def run_validation(
    check_modified: bool = False,
    debug: bool = False,
    strict_mode: bool = False,
    flows_only: bool = False,
    check_prompts: bool = False
) -> ValidationResult:
    """
    Run all validation checks.

    This is a thin wrapper around ValidatorRunner for backward compatibility.

    Args:
        check_modified: If True, only check modified files (git-aware mode)
        debug: If True, print debug information
        strict_mode: If True, enforce swarm design constraints as errors (not warnings)
        flows_only: If True, only run flow validation checks
        check_prompts: If True, validate agent prompt sections (## Inputs, ## Outputs, ## Behavior)

    Returns:
        ValidationResult with all errors and warnings
    """
    # Get modified files if incremental mode
    modified_files = None
    if check_modified:
        if debug:
            print("Debug: Git-aware mode enabled", file=sys.stderr)
        modified_files = get_modified_files()
        if modified_files is None:
            if debug:
                print("Debug: Git unavailable, falling back to full validation", file=sys.stderr)
        elif debug:
            print(f"Debug: Modified files: {len(modified_files)}", file=sys.stderr)

    # Parse registry (always needed, even for flow-only checks)
    try:
        registry = parse_agents_registry()
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: Failed to parse agent registry: {e}", file=sys.stderr)
        sys.exit(EXIT_FATAL_ERROR)

    # Create runner and execute validation
    runner = ValidatorRunner(
        registry=registry,
        modified_files=modified_files,
        debug=debug,
        strict=strict_mode,
        flows_only=flows_only,
        check_prompts=check_prompts,
    )

    return runner.run_all()
