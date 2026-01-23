"""
selftest-core: Core framework for layered selftest governance.

This package provides a reusable framework for implementing layered
selftest governance in any project. It supports:

- Three-tier model: KERNEL (must pass), GOVERNANCE (should pass),
  OPTIONAL (nice-to-have)
- Degraded mode: Allow progress while tracking technical debt
- Doctor diagnostic: Separate environment issues from code issues
- JSON reporting: Machine-parseable reports for CI integration
- Extensible: Add custom steps, checks, and reporters

Quick Start:
    from selftest_core import SelfTestRunner, Step, Tier

    steps = [
        Step(
            id="lint",
            tier=Tier.KERNEL,
            command="ruff check .",
            description="Python linting",
        ),
        Step(
            id="test",
            tier=Tier.KERNEL,
            command="pytest tests/",
            description="Unit tests",
        ),
    ]

    runner = SelfTestRunner(steps)
    result = runner.run()

    if result["status"] == "PASS":
        print("All checks passed!")

Configuration from YAML:
    from selftest_core import load_config, SelfTestRunner

    config = load_config("selftest.yaml")
    runner = SelfTestRunner(config.steps, mode=config.mode)
    result = runner.run()

Diagnostics:
    from selftest_core.doctor import SelfTestDoctor

    doctor = SelfTestDoctor()
    diagnosis = doctor.diagnose()
    doctor.print_diagnosis(diagnosis)
"""

__version__ = "0.1.0"

# Core runner exports
# Configuration exports
from .config import (
    SelftestConfig,
    load_config,
    load_steps_from_list,
    load_steps_from_yaml,
    step_from_dict,
    validate_steps,
)

# Doctor exports
from .doctor import (
    DiagnosticCheck,
    SelfTestDoctor,
    make_command_check,
    make_env_var_check,
    make_python_package_check,
)

# Reporter exports
from .reporter import (
    ConsoleReporter,
    ReportGenerator,
    ReportMetadata,
    ReportSummary,
    StepReport,
)
from .runner import (
    Category,
    SelfTestRunner,
    Severity,
    Step,
    StepResult,
    Tier,
)

__all__ = [
    # Version
    "__version__",
    # Runner
    "SelfTestRunner",
    "Step",
    "StepResult",
    "Tier",
    "Severity",
    "Category",
    # Config
    "SelftestConfig",
    "load_config",
    "load_steps_from_yaml",
    "load_steps_from_list",
    "step_from_dict",
    "validate_steps",
    # Reporter
    "ReportGenerator",
    "ConsoleReporter",
    "ReportMetadata",
    "ReportSummary",
    "StepReport",
    # Doctor
    "SelfTestDoctor",
    "DiagnosticCheck",
    "make_command_check",
    "make_python_package_check",
    "make_env_var_check",
]
