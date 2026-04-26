← [Back to README](../README.md) | [See all docs](./INDEX.md)

# Adopting selftest-core

**What it is:** A layered selftest framework with KERNEL/GOVERNANCE/OPTIONAL tiers, JSON reports, and doctor diagnostics.

**Get started in 3 commands:**

```bash
pip install selftest-core                    # Install
cat > selftest.yaml << 'EOF'                 # Configure
steps:
  - id: lint
    tier: kernel
    command: ruff check .
EOF
selftest run                                 # Run
```

Continue reading for: [Configuration options](#configuration-deep-dive) | [Python API](#python-api-integration) | [CI integration](#cicd-integration) | [Migration guides](#migration-scenarios)

---

## Full TL;DR

Get started in three commands:

```bash
# 1. Install the package
pip install selftest-core

# 2. Create a minimal config
cat > selftest.yaml << 'EOF'
steps:
  - id: lint
    tier: kernel
    command: ruff check .
    description: Python linting
EOF

# 3. Run selftest
selftest run
```

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration Deep Dive](#configuration-deep-dive)
4. [CLI Reference](#cli-reference)
5. [Python API Integration](#python-api-integration)
6. [Adoption Paths](#adoption-paths)
7. [Common Use Cases](#common-use-cases)
8. [Migration Scenarios](#migration-scenarios)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)
11. [Extension Points](#extension-points)

---

## Installation

### From PyPI (pip)

```bash
pip install selftest-core
```

With development dependencies:

```bash
pip install selftest-core[dev]
```

### From PyPI (uv)

```bash
uv pip install selftest-core
```

Or add to your project:

```bash
uv add selftest-core
```

### From Source

```bash
# Clone the repository
git clone https://github.com/EffortlessMetrics/selftest-core.git
cd selftest-core

# Install in development mode
pip install -e .

# Or with uv
uv pip install -e .
```

### Verify Installation

```bash
selftest --version
# Output: selftest-core 0.1.0
```

---

## Quick Start

### Minimal Configuration

Create a `selftest.yaml` file in your project root:

```yaml
steps:
  - id: lint
    tier: kernel
    command: ruff check .
    description: Python linting

  - id: test
    tier: kernel
    command: pytest tests/
    description: Unit tests
```

### Run Selftest

```bash
# Run all steps
selftest run

# Show what would run
selftest plan

# Check environment health
selftest doctor
```

### Example Output

```
RUN  lint                           ... PASS (234ms)
RUN  test                           ... PASS (1523ms)

======================================================================
SELFTEST SUMMARY
======================================================================
Passed:  2/2
Failed:  0/2
Skipped: 0/2

Total time: 1.76s

Status: PASS
```

---

## Configuration Deep Dive

### Configuration File Locations

selftest-core searches for configuration in this order:

1. `selftest.yaml`
2. `selftest.yml`
3. `.selftest.yaml`
4. `.selftest.yml`
5. `selftest_config.yaml`
6. `selftest_config.yml`

Or specify explicitly: `selftest run --config path/to/config.yaml`

### Full YAML Schema

```yaml
# Execution mode: strict (default), degraded, or kernel-only
mode: strict

# Enable verbose output
verbose: false

# Write JSON report after execution
write_report: true

# Report output path
report_path: selftest_report.json

# Step definitions
steps:
  - id: lint                          # Required: Unique step identifier
    tier: kernel                      # Required: kernel, governance, or optional
    command: ruff check .             # Required: Shell command to execute
    description: Python linting       # Optional: Human-readable description
    severity: critical                # Optional: critical, warning (default), info
    category: correctness             # Optional: security, performance, correctness (default), governance
    timeout: 60                       # Optional: Max execution time in seconds (default: 60)
    dependencies: []                  # Optional: List of step IDs that must pass first
    allow_fail_in_degraded: false     # Optional: Treat failure as warning in degraded mode

  - id: typecheck
    tier: kernel
    command: mypy src/
    description: Type checking
    severity: critical
    category: correctness
    dependencies:
      - lint                          # Only runs if 'lint' passes

  - id: test
    tier: kernel
    command: pytest tests/
    description: Unit tests
    timeout: 300                      # Allow 5 minutes for tests
    dependencies:
      - lint
      - typecheck

  - id: security
    tier: governance
    command: pip-audit
    description: Dependency security scan
    severity: warning
    category: security
    allow_fail_in_degraded: true      # Allows progress even if security scan fails

  - id: coverage
    tier: optional
    command: pytest --cov=src --cov-fail-under=80
    description: Coverage threshold
    severity: info
    category: governance
```

### Step Fields Reference

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| `id` | Yes | string | - | Unique step identifier (kebab-case recommended) |
| `tier` | Yes | string | - | `kernel`, `governance`, or `optional` |
| `command` | Yes | string/list | - | Shell command to execute |
| `description` | No | string | `""` | Human-readable description |
| `severity` | No | string | `warning` | `critical`, `warning`, or `info` |
| `category` | No | string | `correctness` | `security`, `performance`, `correctness`, or `governance` |
| `timeout` | No | integer | `60` | Maximum execution time in seconds |
| `dependencies` | No | list | `[]` | Step IDs that must pass before this step runs |
| `allow_fail_in_degraded` | No | boolean | `false` | Treat failure as warning in degraded mode |

### Command as List

Commands can be specified as a list, which will be joined with `&&`:

```yaml
steps:
  - id: setup-and-test
    tier: kernel
    command:
      - pip install -e .
      - pytest tests/
    description: Install and test
```

This executes as: `pip install -e . && pytest tests/`

### Tier Semantics

| Tier | When to Use | Failure Behavior |
|------|-------------|------------------|
| **KERNEL** | Critical checks that must always pass | Blocks in all modes |
| **GOVERNANCE** | Important checks that should pass | Blocks in strict; warns in degraded |
| **OPTIONAL** | Nice-to-have checks | Informational only |

### Execution Modes

| Mode | KERNEL Failure | GOVERNANCE Failure | OPTIONAL Failure |
|------|----------------|-------------------|------------------|
| `strict` | Blocks | Blocks | Informational |
| `degraded` | Blocks | Warning | Informational |
| `kernel-only` | Blocks | Not run | Not run |

---

## CLI Reference

### Commands Overview

```
selftest [OPTIONS] COMMAND [ARGS]

Commands:
  run      Run selftest steps
  plan     Show execution plan
  doctor   Run diagnostics
  list     List available steps

Options:
  --version    Show version and exit
  --help       Show help and exit
```

### selftest run

Execute selftest steps.

```bash
selftest run [OPTIONS]

Options:
  -c, --config PATH    Path to configuration file
  --degraded           Degraded mode: only KERNEL failures block
  --kernel-only        Run only KERNEL tier steps
  --step STEP_ID       Run only the specified step
  -v, --verbose        Verbose output (show errors)
  --json               Output JSON report to stdout
  --json-v2            Output JSON v2 report (with full metadata)
  --report PATH        Write JSON report to file
```

**Examples:**

```bash
# Run all steps in strict mode
selftest run

# Run in degraded mode (GOVERNANCE failures become warnings)
selftest run --degraded

# Run only KERNEL tier steps (fastest)
selftest run --kernel-only

# Run a specific step
selftest run --step lint

# Get JSON output
selftest run --json

# Save report to file
selftest run --report reports/selftest.json

# Use custom config file
selftest run --config ci/selftest-ci.yaml
```

**Exit Codes:**

| Code | Meaning |
|------|---------|
| `0` | All checks passed (PASS) |
| `1` | One or more checks failed (FAIL) |
| `2` | Configuration error |

### selftest plan

Show the execution plan without running.

```bash
selftest plan [OPTIONS]

Options:
  -c, --config PATH    Path to configuration file
  --kernel-only        Show only KERNEL tier steps
  --json               Output JSON plan
```

**Example Output:**

```
======================================================================
SELFTEST PLAN
======================================================================

[1] lint                 [KERNEL    ] [CRITICAL] [CORRECTNESS ] Python linting
[2] typecheck            [KERNEL    ] [CRITICAL] [CORRECTNESS ] Type checking (depends: lint)
[3] test                 [KERNEL    ] [WARNING ] [CORRECTNESS ] Unit tests (depends: lint, typecheck)
[4] security             [GOVERNANCE] [WARNING ] [SECURITY    ] Dependency security scan
[5] coverage             [OPTIONAL  ] [INFO    ] [GOVERNANCE  ] Coverage threshold

Total steps: 5
  KERNEL:     3
  GOVERNANCE: 1
  OPTIONAL:   1
```

### selftest doctor

Run diagnostics to identify environment vs code issues.

```bash
selftest doctor [OPTIONS]

Options:
  --json    Output JSON diagnostics
```

**Example Output:**

```
======================================================================
SELFTEST DOCTOR DIAGNOSTICS
======================================================================

Harness Checks:
  [OK] python_env           : OK
  [OK] git_state            : OK

Service Checks:
  [OK] python_syntax        : OK

======================================================================
Summary: HEALTHY
======================================================================

No issues detected
```

**Diagnostic Summary Values:**

| Summary | Meaning | Action |
|---------|---------|--------|
| `HEALTHY` | All checks pass | Run selftest normally |
| `HARNESS_ISSUE` | Environment problem | Fix environment first |
| `SERVICE_ISSUE` | Code/config broken | Run selftest for details |

### selftest list

List available steps from configuration.

```bash
selftest list [OPTIONS]

Options:
  -c, --config PATH    Path to configuration file
```

**Example Output:**

```
Available steps:
  lint                      [KERNEL    ] Python linting
  typecheck                 [KERNEL    ] Type checking
  test                      [KERNEL    ] Unit tests
  security                  [GOVERNANCE] Dependency security scan
  coverage                  [OPTIONAL  ] Coverage threshold
```

---

## Python API Integration

### Basic Usage

```python
from selftest_core import SelfTestRunner, Step, Tier

# Define steps programmatically
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

# Create runner and execute
runner = SelfTestRunner(steps)
result = runner.run()

# Check result
if result["status"] == "PASS":
    print("All checks passed!")
else:
    print(f"Failed steps: {result['failed_steps']}")
```

### Loading from Configuration

```python
from selftest_core import load_config, SelfTestRunner

# Load from YAML file
config = load_config("selftest.yaml")
runner = SelfTestRunner(config.steps, mode=config.mode)
result = runner.run()

# Or load directly
from selftest_core import load_steps_from_yaml
steps = load_steps_from_yaml("selftest.yaml")
```

### Using Step Callbacks

```python
from selftest_core import SelfTestRunner, Step, Tier, StepResult

def on_start(step: Step):
    print(f"Starting: {step.id}")

def on_complete(step: Step, result: StepResult):
    status = "PASS" if result.status == "PASS" else "FAIL"
    print(f"Completed: {step.id} - {status} ({result.duration_ms}ms)")

runner = SelfTestRunner(
    steps=steps,
    on_step_start=on_start,
    on_step_complete=on_complete,
)
result = runner.run()
```

### Generating Reports

```python
from selftest_core import SelfTestRunner
from selftest_core.reporter import ReportGenerator, ConsoleReporter

runner = SelfTestRunner(steps)
result = runner.run()

# JSON report
generator = ReportGenerator(result)
generator.write_json("reports/selftest.json", version="v2")

# Console output
reporter = ConsoleReporter(result, verbose=True)
reporter.print_full_report()
```

### Custom Diagnostics

```python
from selftest_core.doctor import (
    SelfTestDoctor,
    DiagnosticCheck,
    make_command_check,
    make_python_package_check,
    make_env_var_check,
)

# Create doctor with default checks
doctor = SelfTestDoctor()

# Add custom checks
doctor.add_check(make_command_check(
    name="docker",
    command="docker --version",
    error_message="Install Docker: https://docs.docker.com/get-docker/",
))

doctor.add_check(make_python_package_check("numpy"))

doctor.add_check(make_env_var_check("DATABASE_URL", required=True))

# Add fully custom check
doctor.add_check(DiagnosticCheck(
    name="database_connection",
    category="service",
    check_fn=lambda: ("OK", None) if db_ping() else ("ERROR", "Database unreachable"),
))

# Run diagnostics
diagnosis = doctor.diagnose()
doctor.print_diagnosis(diagnosis)
```

### Validating Steps

```python
from selftest_core import validate_steps, Step, Tier

steps = [
    Step(id="a", tier=Tier.KERNEL, command="true"),
    Step(id="b", tier=Tier.KERNEL, command="true", dependencies=["a"]),
    Step(id="c", tier=Tier.KERNEL, command="true", dependencies=["nonexistent"]),
]

errors = validate_steps(steps)
if errors:
    for error in errors:
        print(f"Validation error: {error}")
# Output: Validation error: Step 'c' has invalid dependency 'nonexistent'
```

### Execution Plan

```python
runner = SelfTestRunner(steps, mode="kernel-only")
plan = runner.plan()

print(f"Total steps: {plan['summary']['total']}")
print(f"By tier: {plan['summary']['by_tier']}")
```

---

## Adoption Paths

### Path 1: Minimal CLI (Fastest Start)

For teams wanting immediate validation without Python integration.

**Setup time:** 5 minutes

1. Install: `pip install selftest-core`
2. Create `selftest.yaml` with basic steps
3. Add to CI: `selftest run`

**Best for:**
- Small projects
- Single-language repos
- Teams new to layered testing

**Example:**

```yaml
# selftest.yaml
steps:
  - id: lint
    tier: kernel
    command: ruff check .
  - id: test
    tier: kernel
    command: pytest
```

### Path 2: Intermediate Python Integration

For teams wanting programmatic control and custom reporting.

**Setup time:** 30 minutes

1. Install: `pip install selftest-core`
2. Create Python wrapper script
3. Integrate with existing test infrastructure

**Best for:**
- Medium-sized projects
- Custom CI/CD pipelines
- Teams with existing Python tooling

**Example:**

```python
# scripts/run_selftest.py
from selftest_core import load_config, SelfTestRunner
from selftest_core.reporter import ReportGenerator
import sys

config = load_config("selftest.yaml")
runner = SelfTestRunner(config.steps, mode=config.mode)
result = runner.run()

# Generate report
generator = ReportGenerator(result)
generator.write_json("reports/selftest.json")

# Custom handling
if not result["kernel_ok"]:
    print("KERNEL failure - blocking merge")
    sys.exit(1)
elif not result["governance_ok"]:
    print("GOVERNANCE issues - review before merge")
    sys.exit(0 if result["status"] == "PASS" else 1)
```

### Path 3: Advanced Diagnostics

For teams needing environment validation and custom health checks.

**Setup time:** 1 hour

1. Install: `pip install selftest-core`
2. Create custom doctor configuration
3. Add project-specific checks
4. Integrate with CI and developer workflow

**Best for:**
- Large projects with complex environments
- Multi-service architectures
- Teams with frequent environment issues

**Example:**

```python
# scripts/selftest_doctor.py
from selftest_core.doctor import (
    SelfTestDoctor,
    make_command_check,
    make_python_package_check,
    make_env_var_check,
)

def create_project_doctor():
    doctor = SelfTestDoctor()

    # Environment checks
    doctor.add_check(make_command_check("docker", "docker --version"))
    doctor.add_check(make_command_check("kubectl", "kubectl version --client"))
    doctor.add_check(make_env_var_check("AWS_PROFILE", required=True))

    # Python dependencies
    for pkg in ["pytest", "ruff", "mypy"]:
        doctor.add_check(make_python_package_check(pkg))

    return doctor

if __name__ == "__main__":
    doctor = create_project_doctor()
    diagnosis = doctor.diagnose()
    doctor.print_diagnosis(diagnosis)
    exit(0 if diagnosis["summary"] == "HEALTHY" else 1)
```

---

## Common Use Cases

### Custom Checks

Create steps for project-specific validation:

```yaml
steps:
  # Database migrations
  - id: migrations
    tier: kernel
    command: python manage.py migrate --check
    description: Check pending migrations
    category: governance

  # API contract validation
  - id: openapi-validate
    tier: governance
    command: openapi-spec-validator api/openapi.yaml
    description: Validate OpenAPI spec
    category: correctness

  # Docker build test
  - id: docker-build
    tier: governance
    command: docker build -t myapp:test .
    description: Test Docker build
    timeout: 300
    category: correctness
```

### CI/CD Integration

#### GitHub Actions

```yaml
name: Selftest

on: [push, pull_request]

jobs:
  kernel-smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install selftest-core
      - run: selftest run --kernel-only

  full-selftest:
    runs-on: ubuntu-latest
    needs: kernel-smoke
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install selftest-core
      - run: selftest run --report selftest_report.json
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: selftest-report
          path: selftest_report.json
```

#### GitLab CI

```yaml
stages:
  - smoke
  - test

kernel-smoke:
  stage: smoke
  script:
    - pip install selftest-core
    - selftest run --kernel-only

selftest:
  stage: test
  needs: [kernel-smoke]
  script:
    - pip install selftest-core
    - selftest run --report selftest_report.json
  artifacts:
    when: always
    paths:
      - selftest_report.json
```

### Dashboard Integration

Parse JSON output for dashboards:

```bash
# Check overall status
selftest run --json | jq '.status'

# Get failed steps
selftest run --json | jq '.failed_steps'

# Get timing information
selftest run --json-v2 | jq '.summary.total_duration_ms'

# Get breakdown by severity
selftest run --json-v2 | jq '.summary.by_severity'
```

### Makefile Integration

```makefile
.PHONY: selftest selftest-degraded kernel-smoke selftest-doctor

selftest:
	selftest run

selftest-degraded:
	selftest run --degraded

kernel-smoke:
	selftest run --kernel-only

selftest-doctor:
	selftest doctor

selftest-report:
	selftest run --report reports/selftest-$(shell date +%Y%m%d).json
```

---

## Migration Scenarios

### From Makefile-based Testing

**Before (Makefile):**

```makefile
.PHONY: lint test check

lint:
	ruff check .

test:
	pytest tests/

check: lint test
```

**After (selftest.yaml):**

```yaml
steps:
  - id: lint
    tier: kernel
    command: ruff check .
    description: Python linting

  - id: test
    tier: kernel
    command: pytest tests/
    description: Unit tests
    dependencies:
      - lint
```

**Migration steps:**

1. Create `selftest.yaml` with equivalent steps
2. Map dependencies (Makefile `check: lint test` becomes `dependencies: [lint]`)
3. Add tier assignments based on criticality
4. Update CI to use `selftest run` instead of `make check`
5. Keep Makefile as convenience wrapper: `check: ; selftest run`

### From Homegrown Test Runners

**Before (custom script):**

```python
# run_tests.py
import subprocess
import sys

def run_checks():
    checks = [
        ("lint", "ruff check ."),
        ("test", "pytest tests/"),
        ("security", "pip-audit"),
    ]

    failed = []
    for name, cmd in checks:
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            failed.append(name)

    return len(failed) == 0
```

**After (selftest.yaml):**

```yaml
steps:
  - id: lint
    tier: kernel
    command: ruff check .

  - id: test
    tier: kernel
    command: pytest tests/

  - id: security
    tier: governance
    command: pip-audit
    allow_fail_in_degraded: true
```

**Migration benefits:**

- Tier-based governance (KERNEL vs GOVERNANCE vs OPTIONAL)
- Degraded mode for progress during incidents
- JSON reporting for dashboards
- Doctor diagnostics for environment issues
- Dependency management between steps

### From pytest-only to Layered Testing

**Before:**

```bash
# CI runs everything in one pytest invocation
pytest tests/ --cov=src --cov-fail-under=80
```

**After:**

```yaml
steps:
  # KERNEL: Fast, critical checks
  - id: lint
    tier: kernel
    command: ruff check .
    description: Linting

  - id: typecheck
    tier: kernel
    command: mypy src/
    description: Type checking

  - id: unit-tests
    tier: kernel
    command: pytest tests/unit/ -x
    description: Unit tests (fail fast)

  # GOVERNANCE: Important but slower
  - id: integration-tests
    tier: governance
    command: pytest tests/integration/
    description: Integration tests
    timeout: 300

  - id: security
    tier: governance
    command: pip-audit
    description: Dependency security

  # OPTIONAL: Nice to have
  - id: coverage
    tier: optional
    command: pytest tests/ --cov=src --cov-fail-under=80
    description: Coverage threshold
```

---

## Troubleshooting

### Common Issues

#### "No steps configured"

**Error:**

```
Error: No steps configured.
Create a selftest.yaml file or use --config to specify one.
```

**Fix:** Create a `selftest.yaml` file or specify config path:

```bash
selftest run --config path/to/config.yaml
```

#### "Unknown step"

**Error:**

```
Error: Unknown step 'typo-step'
Available steps: lint, test, security
```

**Fix:** Check step ID spelling. Use `selftest list` to see available steps.

#### Step Timeout

**Error:**

```
FAIL (timeout after 60s)
```

**Fix:** Increase timeout in configuration:

```yaml
steps:
  - id: slow-test
    tier: kernel
    command: pytest tests/
    timeout: 300  # 5 minutes
```

#### Dependency Not Satisfied

**Output:**

```
[SKIP] integration-tests (Dependency not satisfied)
```

**Cause:** A dependency step failed.

**Fix:** Fix the failing dependency step first, or remove the dependency.

#### HARNESS_ISSUE in Doctor

**Output:**

```
Summary: HARNESS_ISSUE

Recommendations:
  1. Upgrade to Python 3.10+
```

**Fix:** Address environment issues before running selftest. The doctor identifies what needs fixing.

### Debug Mode

Enable verbose output for more details:

```bash
selftest run --verbose
```

### JSON Diagnostics

Get machine-readable diagnostics:

```bash
selftest doctor --json | jq '.recommendations'
```

### Validating Configuration

Check for configuration errors before running:

```bash
selftest plan
```

This will fail fast if configuration is invalid.

---

## Best Practices

### 1. Start with KERNEL Tier

Begin with the most critical checks as KERNEL:

```yaml
steps:
  - id: compile
    tier: kernel
    command: python -m compileall src/

  - id: lint
    tier: kernel
    command: ruff check .
```

### 2. Use Dependencies Wisely

Only add dependencies when order truly matters:

```yaml
steps:
  - id: lint
    tier: kernel
    command: ruff check .

  - id: test
    tier: kernel
    command: pytest tests/
    dependencies:
      - lint  # Only if lint failure means tests are meaningless
```

### 3. Set Appropriate Timeouts

Default is 60 seconds. Adjust for slow operations:

```yaml
steps:
  - id: integration-tests
    tier: governance
    command: pytest tests/integration/
    timeout: 600  # 10 minutes
```

### 4. Use Degraded Mode Thoughtfully

Mark steps that can fail during incidents:

```yaml
steps:
  - id: external-api-test
    tier: governance
    command: pytest tests/external/
    allow_fail_in_degraded: true  # External API might be down
```

### 5. Keep KERNEL Fast

KERNEL steps should complete quickly for fast feedback:

```yaml
steps:
  # Good: Fast lint check
  - id: lint
    tier: kernel
    command: ruff check .

  # Bad: Slow full test suite as KERNEL
  # - id: all-tests
  #   tier: kernel
  #   command: pytest tests/  # Could take 10 minutes
```

### 6. Use Severity and Category

Classify steps for better reporting:

```yaml
steps:
  - id: security-scan
    tier: governance
    command: pip-audit
    severity: critical
    category: security

  - id: performance-test
    tier: optional
    command: pytest tests/perf/
    severity: info
    category: performance
```

### 7. Document Steps

Add descriptions for clarity:

```yaml
steps:
  - id: migrations
    tier: kernel
    command: python manage.py migrate --check
    description: Verify no pending database migrations
```

### 8. Run Doctor Before Selftest

In CI, run doctor first to catch environment issues:

```yaml
# CI workflow
- run: selftest doctor
- run: selftest run
```

---

## Extension Points

### Custom Diagnostic Checks

Create project-specific health checks:

```python
from selftest_core.doctor import DiagnosticCheck, SelfTestDoctor

def check_database() -> tuple:
    """Check database connectivity."""
    try:
        # Your database check logic
        conn = create_connection()
        conn.execute("SELECT 1")
        return ("OK", None)
    except Exception as e:
        return ("ERROR", f"Database unreachable: {e}")

doctor = SelfTestDoctor()
doctor.add_check(DiagnosticCheck(
    name="database",
    category="service",
    check_fn=check_database,
))
```

### Custom Reporters

Create custom output formats:

```python
from selftest_core.reporter import ReportGenerator
import defusedxml.ElementTree as ET  # SECURITY: Use defusedxml to prevent XXE vulnerabilities.

class JUnitReporter:
    """Generate JUnit XML reports for CI systems."""

    def __init__(self, result: dict):
        self.result = result

    def to_xml(self) -> str:
        root = ET.Element("testsuite")
        root.set("name", "selftest")
        root.set("tests", str(self.result["total"]))
        root.set("failures", str(self.result["failed"]))

        for step in self.result["results"]:
            testcase = ET.SubElement(root, "testcase")
            testcase.set("name", step["step_id"])
            testcase.set("time", str(step["duration_ms"] / 1000))

            if step["status"] == "FAIL":
                failure = ET.SubElement(testcase, "failure")
                failure.text = step.get("error", "Unknown error")

        return ET.tostring(root, encoding="unicode")
```

### Custom Step Execution

Override step execution for special handling:

```python
from selftest_core import SelfTestRunner, Step, StepResult
import time

class CustomRunner(SelfTestRunner):
    """Runner with custom step execution."""

    def run_step(self, step: Step) -> StepResult:
        # Custom pre-step logic
        print(f"[{time.strftime('%H:%M:%S')}] Running: {step.id}")

        # Call parent implementation
        result = super().run_step(step)

        # Custom post-step logic
        if result.status == "FAIL":
            self.send_alert(step, result)

        return result

    def send_alert(self, step: Step, result: StepResult):
        """Send alert on failure."""
        # Your alerting logic
        pass
```

### Integration with External Systems

Hook into external systems via callbacks:

```python
from selftest_core import SelfTestRunner, Step, StepResult
import requests

def notify_slack(step: Step, result: StepResult):
    """Send Slack notification on failure."""
    if result.status == "FAIL":
        requests.post(
            "https://hooks.slack.com/...",
            json={"text": f"Selftest failed: {step.id}"}
        )

runner = SelfTestRunner(
    steps=steps,
    on_step_complete=notify_slack,
)
```

### Environment-Specific Configuration

Load different configurations per environment:

```python
import os
from selftest_core import load_config

env = os.environ.get("ENVIRONMENT", "development")
config_file = f"selftest-{env}.yaml"

config = load_config(config_file)
```

---

## Summary

selftest-core provides a flexible, layered approach to project validation:

- **Three tiers** (KERNEL/GOVERNANCE/OPTIONAL) for graduated governance
- **Three modes** (strict/degraded/kernel-only) for different scenarios
- **Doctor diagnostics** to separate environment from code issues
- **JSON reporting** for CI/CD and dashboard integration
- **Python API** for programmatic control
- **Extensible** with custom checks, reporters, and runners

Start simple with CLI and YAML, then grow into Python integration as needs evolve.

---

## References

- [selftest-core README](../packages/selftest-core/README.md)
- [Selftest System Documentation](../swarm/SELFTEST_SYSTEM.md)
- [Cross-Repo Template Design](./designs/CROSS_REPO_TEMPLATE_DESIGN.md)
