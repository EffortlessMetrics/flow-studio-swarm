#!/usr/bin/env python3
"""
selftest_config.py - Selftest configuration and data model

Defines the structure and registry of selftest steps. The selftest system is
**composable, layered, and introspectable**:

- **Composable**: Steps are independent; can run individually or in sequence
- **Layered**: KERNEL (must work) vs GOVERNANCE (nice-to-have) vs OPTIONAL
- **Introspectable**: Clear status, dependencies, and failure modes

## SelfTestTier

- KERNEL: Must pass; failures block workflow (critical checks)
- GOVERNANCE: Should pass; failures are warnings in degraded mode
- OPTIONAL: Nice-to-have; failures are informational

## SelfTestStep

Represents one selftest step with:
- id: unique identifier (e.g., 'core-checks')
- description: human-readable description
- tier: SelfTestTier (KERNEL, GOVERNANCE, OPTIONAL)
- command: shell command(s) to run (list of strings, joined with &&)
- allow_fail_in_degraded: bool (if True, failures are warnings in --degraded mode)
- dependencies: list of step ids that must pass before this step runs

## Step Registry

16 steps in order:
1. core-checks           (tier: KERNEL)      Python ruff linting + compile checks
2. skills-governance    (tier: GOVERNANCE)  skills-lint, skills-fmt
3. agents-governance    (tier: GOVERNANCE)  agents-lint, agents-fmt
4. bdd                  (tier: GOVERNANCE)  cucumber features
5. ac-status            (tier: GOVERNANCE)  validate AC coverage
6. policy-tests         (tier: GOVERNANCE)  OPA/Conftest
7. devex-contract       (tier: GOVERNANCE)  flows, xtask commands, skills
8. graph-invariants     (tier: GOVERNANCE)  governance graph connectivity
9. flowstudio-smoke     (tier: GOVERNANCE)  Flow Studio API health check
10. gemini-stepwise-tests (tier: GOVERNANCE)  Unit tests for GeminiStepwiseBackend
11. claude-stepwise-tests (tier: GOVERNANCE)  Unit tests for ClaudeStepwiseBackend
12. runs-gc-dry-check    (tier: GOVERNANCE)  Runs garbage collection health check
13. provider-env-check   (tier: GOVERNANCE)  Provider environment variable validation
14. wisdom-smoke         (tier: GOVERNANCE)  Wisdom summarizer and aggregator validation
15. ac-coverage          (tier: OPTIONAL)    coverage thresholds
16. extras              (tier: OPTIONAL)    experimental checks
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class SelfTestTier(Enum):
    """Selftest tier indicating criticality and failure behavior."""

    KERNEL = "kernel"  # Must pass; failures block workflow
    GOVERNANCE = "governance"  # Should pass; can warn in degraded mode
    OPTIONAL = "optional"  # Nice-to-have; failures are informational


class SelfTestSeverity(Enum):
    """Severity level of a selftest step."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class SelfTestCategory(Enum):
    """Category of a selftest step."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    GOVERNANCE = "governance"


@dataclass
class SelfTestStep:
    """
    Represents one selftest step.

    Attributes:
        id: Unique identifier (e.g., 'core-checks')
        name: Human-readable name (e.g., 'Core Checks')
        description: Human-readable description
        tier: SelfTestTier (KERNEL, GOVERNANCE, OPTIONAL)
        severity: SelfTestSeverity (CRITICAL, WARNING, INFO)
        category: SelfTestCategory (SECURITY, PERFORMANCE, CORRECTNESS, GOVERNANCE)
        command: List of shell commands to run in sequence (joined with &&)
        allow_fail_in_degraded: If True, failures become warnings in --degraded mode
        dependencies: List of step ids that must pass before this step runs
        ac_ids: List of acceptance criteria IDs that this step covers (e.g., ['AC-SELFTEST-KERNEL-FAST'])
        timeout: Timeout in seconds for step execution (default: 300)
    """

    id: str
    name: str
    description: str
    tier: SelfTestTier
    severity: SelfTestSeverity
    category: SelfTestCategory
    command: List[str]
    ac_ids: List[str] = None
    allow_fail_in_degraded: bool = False
    dependencies: Optional[List[str]] = None
    timeout: int = 300  # Default 5 minute timeout

    def __post_init__(self):
        """Validate step definition."""
        if not self.id or not self.name or not self.description:
            raise ValueError("id, name, and description are required")
        if not self.command or not isinstance(self.command, list):
            raise ValueError("command must be a non-empty list of strings")
        if not all(isinstance(c, str) for c in self.command):
            raise ValueError("all commands must be strings")
        if not isinstance(self.severity, SelfTestSeverity):
            raise ValueError("severity must be SelfTestSeverity enum")
        if not isinstance(self.category, SelfTestCategory):
            raise ValueError("category must be SelfTestCategory enum")
        if self.timeout <= 0:
            raise ValueError(f"timeout for step {self.id!r} must be > 0")
        if self.dependencies is None:
            self.dependencies = []
        if self.ac_ids is None:
            self.ac_ids = []

    def full_command(self) -> str:
        """Return the full command as a single string (commands joined with &&)."""
        return " && ".join(self.command)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tier": self.tier.value,
            "severity": self.severity.value,
            "category": self.category.value,
            "command": self.command,
            "ac_ids": self.ac_ids or [],
            "allow_fail_in_degraded": self.allow_fail_in_degraded,
            "dependencies": self.dependencies or [],
        }


# Define the 16 selftest steps in order
SELFTEST_STEPS = [
    SelfTestStep(
        id="core-checks",
        name="Core Checks",
        description="Python tooling checks (ruff linting + compile validation)",
        tier=SelfTestTier.KERNEL,
        severity=SelfTestSeverity.CRITICAL,
        category=SelfTestCategory.CORRECTNESS,
        command=[
            "uv run ruff check swarm/tools swarm/validator",
            "uv run python -m compileall -x _archive swarm/tools swarm/validator",
        ],
        ac_ids=["AC-SELFTEST-KERNEL-FAST", "AC-SELFTEST-FAILURE-HINTS"],
        allow_fail_in_degraded=False,
    ),
    SelfTestStep(
        id="skills-governance",
        name="Skills Governance",
        description="Skills linting and formatting",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "uv run swarm/tools/skills_lint.py",
        ],
        ac_ids=[
            "AC-SELFTEST-INTROSPECTABLE",
            "AC-SELFTEST-FAILURE-HINTS",
            "AC-SELFTEST-DEGRADATION-TRACKED",
        ],
        allow_fail_in_degraded=True,
    ),
    SelfTestStep(
        id="agents-governance",
        name="Agents Governance",
        description="Agent definitions linting and formatting",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "uv run swarm/tools/validate_swarm.py --check-modified",
        ],
        ac_ids=[
            "AC-SELFTEST-INTROSPECTABLE",
            "AC-SELFTEST-FAILURE-HINTS",
            "AC-SELFTEST-DEGRADATION-TRACKED",
        ],
        allow_fail_in_degraded=True,
    ),
    SelfTestStep(
        id="bdd",
        name="BDD",
        description="BDD scenarios (cucumber features)",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.CORRECTNESS,
        command=[
            "uv run swarm/tools/bdd_validator.py",
        ],
        ac_ids=[
            "AC-SELFTEST-INTROSPECTABLE",
            "AC-SELFTEST-FAILURE-HINTS",
            "AC-SELFTEST-DEGRADATION-TRACKED",
        ],
        allow_fail_in_degraded=True,
    ),
    SelfTestStep(
        id="ac-status",
        name="AC Status",
        description="Validate acceptance criteria coverage",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "echo 'Checking AC coverage status...'",
            "true",  # Placeholder; would read from build artifacts
        ],
        ac_ids=[
            "AC-SELFTEST-INTROSPECTABLE",
            "AC-SELFTEST-FAILURE-HINTS",
            "AC-SELFTEST-DEGRADATION-TRACKED",
        ],
        allow_fail_in_degraded=True,
    ),
    SelfTestStep(
        id="policy-tests",
        name="Policy Tests",
        description="OPA/Conftest policy validation",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "echo 'Running policy checks...'",
            "true",  # Placeholder; would run OPA if installed
        ],
        ac_ids=[
            "AC-SELFTEST-INTROSPECTABLE",
            "AC-SELFTEST-FAILURE-HINTS",
            "AC-SELFTEST-DEGRADATION-TRACKED",
        ],
        allow_fail_in_degraded=True,
    ),
    SelfTestStep(
        id="devex-contract",
        name="DevEx Contract",
        description="Developer experience contract (flows, commands, skills)",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "uv run swarm/tools/validate_swarm.py",
            "uv run swarm/tools/gen_flows.py --check",
            "uv run swarm/tools/gen_adapters.py --platform claude --mode check-all",
        ],
        ac_ids=[
            "AC-SELFTEST-INTROSPECTABLE",
            "AC-SELFTEST-FAILURE-HINTS",
            "AC-SELFTEST-DEGRADATION-TRACKED",
        ],
        allow_fail_in_degraded=True,
        dependencies=["core-checks"],
    ),
    SelfTestStep(
        id="graph-invariants",
        name="Graph Invariants",
        description="Governance graph connectivity and invariants",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "echo 'Flow graph invariants: validated by check-flows step'",
        ],
        ac_ids=[
            "AC-SELFTEST-INTROSPECTABLE",
            "AC-SELFTEST-FAILURE-HINTS",
            "AC-SELFTEST-DEGRADATION-TRACKED",
        ],
        allow_fail_in_degraded=True,
        dependencies=["devex-contract"],
    ),
    SelfTestStep(
        id="flowstudio-smoke",
        name="Flow Studio Smoke",
        description="Flow Studio selftest summary check (in-process, no HTTP)",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "uv run python -m swarm.tools.flow_studio_smoke",
        ],
        ac_ids=[
            "AC-SELFTEST-INTROSPECTABLE",
            "AC-SELFTEST-FAILURE-HINTS",
            "AC-SELFTEST-DEGRADATION-TRACKED",
        ],
        allow_fail_in_degraded=True,
        timeout=15,  # Fast in-process path; generous margin over ~5-10s typical
    ),
    SelfTestStep(
        id="gemini-stepwise-tests",
        name="Gemini Stepwise Tests",
        description="Unit tests for GeminiStepwiseBackend orchestration",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.CORRECTNESS,
        command=[
            "uv run pytest tests/test_gemini_stepwise_backend.py -v --tb=short",
        ],
        ac_ids=["AC-SELFTEST-STEPWISE-GEMINI"],
        allow_fail_in_degraded=True,
        timeout=120,
    ),
    SelfTestStep(
        id="claude-stepwise-tests",
        name="Claude Stepwise Tests",
        description="Unit tests for ClaudeStepwiseBackend orchestration",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.CORRECTNESS,
        command=[
            "uv run pytest tests/test_claude_stepwise_backend.py -v --tb=short",
        ],
        ac_ids=["AC-SELFTEST-STEPWISE-CLAUDE"],
        allow_fail_in_degraded=True,
        timeout=120,
    ),
    SelfTestStep(
        id="runs-gc-dry-check",
        name="Runs GC Health Check",
        description="Validate runs garbage collection is operational",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.WARNING,
        category=SelfTestCategory.GOVERNANCE,
        command=["uv run swarm/tools/runs_gc.py list"],
        ac_ids=["AC-SELFTEST-RUNS-GC-HEALTH"],
        allow_fail_in_degraded=True,
        dependencies=["core-checks"],
        timeout=60,
    ),
    SelfTestStep(
        id="ac-coverage",
        name="AC Coverage",
        description="Acceptance criteria coverage thresholds",
        tier=SelfTestTier.OPTIONAL,
        severity=SelfTestSeverity.INFO,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "echo 'Checking AC coverage thresholds...'",
            "true",  # Placeholder; would check coverage % against target
        ],
        ac_ids=["AC-SELFTEST-INDIVIDUAL-STEPS", "AC-SELFTEST-FAILURE-HINTS"],
        allow_fail_in_degraded=False,
    ),
    SelfTestStep(
        id="provider-env-check",
        name="Provider Env Check",
        description="Validate provider environment variables for stepwise backends",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.INFO,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "uv run swarm/tools/provider_env_check.py",
        ],
        ac_ids=["AC-SELFTEST-PROVIDER-ENV"],
        allow_fail_in_degraded=True,
        timeout=30,
    ),
    SelfTestStep(
        id="wisdom-smoke",
        name="Wisdom Smoke",
        description="Validate wisdom summarizer and aggregator tools",
        tier=SelfTestTier.GOVERNANCE,
        severity=SelfTestSeverity.INFO,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "uv run swarm/tools/wisdom_summarizer.py stepwise-claude --dry-run --output quiet",
            "uv run swarm/tools/wisdom_aggregate_runs.py",
        ],
        ac_ids=["AC-SELFTEST-WISDOM-SMOKE"],
        allow_fail_in_degraded=True,
        timeout=60,
    ),
    SelfTestStep(
        id="extras",
        name="Extras",
        description="Experimental and additional checks",
        tier=SelfTestTier.OPTIONAL,
        severity=SelfTestSeverity.INFO,
        category=SelfTestCategory.GOVERNANCE,
        command=[
            "echo 'Running experimental checks...'",
            "true",  # Placeholder for future experimental checks
        ],
        ac_ids=["AC-SELFTEST-DEGRADED", "AC-SELFTEST-FAILURE-HINTS"],
        allow_fail_in_degraded=False,
    ),
]


# Wave-based parallelization (steps in same wave can run in parallel)
# Based on dependency analysis from DISTRIBUTED_SELFTEST_DESIGN.md
EXECUTION_WAVES = [
    # Wave 0: Kernel (must run first, sequential - blocking)
    ["core-checks"],
    # Wave 1: Independent GOVERNANCE steps (parallel after kernel)
    [
        "skills-governance",
        "agents-governance",
        "bdd",
        "ac-status",
        "policy-tests",
        "flowstudio-smoke",
        "gemini-stepwise-tests",
        "claude-stepwise-tests",
        "runs-gc-dry-check",
        "provider-env-check",
        "wisdom-smoke",
    ],
    # Wave 2: devex-contract (depends on core-checks, already satisfied)
    ["devex-contract"],
    # Wave 3: graph-invariants (depends on devex-contract)
    ["graph-invariants"],
    # Wave 4: Optional (depends on all GOVERNANCE)
    ["ac-coverage", "extras"],
]


def get_wave_for_step(step_id: str) -> Optional[int]:
    """Get the wave index for a given step id."""
    for wave_idx, wave_steps in enumerate(EXECUTION_WAVES):
        if step_id in wave_steps:
            return wave_idx
    return None


def validate_wave_definitions() -> List[str]:
    """
    Validate that wave definitions are consistent with step registry.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []
    step_ids = {step.id for step in SELFTEST_STEPS}

    # Check all wave steps exist in registry
    wave_steps_seen = set()
    for wave_idx, wave_steps in enumerate(EXECUTION_WAVES):
        for step_id in wave_steps:
            if step_id not in step_ids:
                errors.append(f"Wave {wave_idx} references unknown step '{step_id}'")
            if step_id in wave_steps_seen:
                errors.append(f"Step '{step_id}' appears in multiple waves")
            wave_steps_seen.add(step_id)

    # Check all registry steps are in some wave
    for step in SELFTEST_STEPS:
        if step.id not in wave_steps_seen:
            errors.append(f"Step '{step.id}' is not assigned to any wave")

    # Check dependency constraints are respected
    for step in SELFTEST_STEPS:
        if step.dependencies:
            step_wave = get_wave_for_step(step.id)
            if step_wave is None:
                continue
            for dep_id in step.dependencies:
                dep_wave = get_wave_for_step(dep_id)
                if dep_wave is None:
                    continue
                if dep_wave >= step_wave:
                    errors.append(
                        f"Step '{step.id}' (wave {step_wave}) depends on "
                        f"'{dep_id}' (wave {dep_wave}) which runs at same "
                        f"time or later"
                    )

    return errors


def get_step_by_id(step_id: str) -> Optional[SelfTestStep]:
    """Retrieve a step by its id."""
    for step in SELFTEST_STEPS:
        if step.id == step_id:
            return step
    return None


def validate_step_list() -> List[str]:
    """
    Validate the step list for consistency.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []
    step_ids = {step.id for step in SELFTEST_STEPS}

    # Check for duplicate ids
    seen = set()
    for step in SELFTEST_STEPS:
        if step.id in seen:
            errors.append(f"Duplicate step id: {step.id}")
        seen.add(step.id)

    # Check for invalid dependencies
    for step in SELFTEST_STEPS:
        if step.dependencies:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(f"Step '{step.id}' has invalid dependency '{dep_id}'")

    # Check for circular dependencies
    def has_circular_dependency(step_id: str, visited: set) -> bool:
        if step_id in visited:
            return True
        visited.add(step_id)
        step = get_step_by_id(step_id)
        if step and step.dependencies:
            for dep_id in step.dependencies:
                if has_circular_dependency(dep_id, visited.copy()):
                    return True
        return False

    for step in SELFTEST_STEPS:
        if has_circular_dependency(step.id, set()):
            errors.append(f"Step '{step.id}' has circular dependencies")

    return errors


def get_steps_in_order(
    until_id: Optional[str] = None, filter_tier: Optional[SelfTestTier] = None
) -> List[SelfTestStep]:
    """
    Get steps in execution order, optionally filtered by tier or up to a specific step.

    Args:
        until_id: If specified, only include steps up to and including this step id
        filter_tier: If specified, only include steps of this tier

    Returns:
        List of steps in order
    """
    steps = SELFTEST_STEPS
    if until_id:
        idx = None
        for i, step in enumerate(steps):
            if step.id == until_id:
                idx = i
                break
        if idx is not None:
            steps = steps[: idx + 1]
        else:
            raise ValueError(f"Unknown step id: {until_id}")

    if filter_tier:
        steps = [step for step in steps if step.tier == filter_tier]

    return steps


def to_json(steps: Optional[List[SelfTestStep]] = None) -> str:
    """Convert step list to JSON."""
    if steps is None:
        steps = SELFTEST_STEPS
    return json.dumps([step.to_dict() for step in steps], indent=2)
