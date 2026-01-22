# CI/CD Troubleshooting Guide

This guide helps you diagnose and resolve CI/CD issues in the Swarm demo repo. Whether a check is failing in GitHub Actions or you need to reproduce an issue locally, start here.

**Quick links:**
- **Selftest diagnostic**: `make selftest-doctor` — Separates harness issues from code issues
- **AC freshness check**: `make check-ac-freshness` — Validates AC matrix alignment
- **All workflows**: `.github/workflows/` — Three main CI workflows

---

## Quick Reference: CI Jobs and Local Commands

This table maps every CI job to its local equivalent. Use it to reproduce CI failures on your machine.

| CI Job | Workflow | Local Command | Purpose |
|--------|----------|---------------|---------|
| **validate-swarm** | `ci.yml` | `make validate-swarm` | Validate agent/flow spec alignment |
| **test-swarm** | `ci.yml` | `uv run pytest` | Run Python unit and integration tests |
| **[GOVERNANCE] Check AC Matrix Freshness** | `selftest-governance-gate.yml` | `make check-ac-freshness` | Validate AC matrix is in sync with implementation |
| **[GOVERNANCE] Run AC Tests** | `selftest-governance-gate.yml` | `uv run pytest tests/test_selftest_ac_*.py -v` | Run AC bijection, API contract, traceability tests |
| **[GOVERNANCE] Run Degradation Tests** | `selftest-governance-gate.yml` | `uv run pytest tests/test_selftest_degradation_*.py -v` | Run degradation schema, CLI, and status coherence tests |
| **[OPTIONAL] Run Selftest Doctor** | `selftest-governance-gate.yml` | `make selftest-doctor` | Diagnostic tool (informational, non-blocking) |

---

## Reproducing CI Issues Locally

### 1. Set Up the Same Environment as CI

CI uses Python 3.13 with UV for dependency management. Replicate this locally:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify Python version
python --version  # Should be 3.13+

# Sync dependencies with frozen lockfile (same as CI)
uv sync --frozen

# Optional: Include dev dependencies for testing
uv sync --frozen --extra dev
```

### 2. Run the Same Commands as CI

Run the exact commands that CI runs, in the same order:

**Basic validation (from ci.yml):**

```bash
# Step 1: Validate swarm spec
make validate-swarm

# Step 2: Run Python tests
uv run pytest
```

**Governance gate (from selftest-governance-gate.yml):**

```bash
# Step 1: AC matrix freshness
make check-ac-freshness

# Step 2: AC-related tests
uv run pytest \
  tests/test_selftest_ac_bijection.py \
  tests/test_selftest_ac_traceability.py \
  tests/test_selftest_api_contract.py \
  tests/test_selftest_api_contract_coherence.py \
  -v --tb=short --color=yes

# Step 3: Degradation system tests
uv run pytest \
  tests/test_selftest_degradation_schema_compliance.py \
  tests/test_selftest_degradations_cli_contract.py \
  tests/test_selftest_status_degradation_coherence.py \
  tests/test_selftest_degradation_log.py \
  -v --tb=short --color=yes
```

**Full development check (combines all):**

```bash
make dev-check
```

### 3. Isolate the Problem

If a test is failing, isolate which step:

```bash
# Run just one test file
uv run pytest tests/test_selftest_ac_bijection.py -v

# Run one specific test
uv run pytest tests/test_selftest_ac_bijection.py::test_ac_exists_in_matrix -v

# Show full output and stack traces
uv run pytest tests/test_selftest_ac_bijection.py -vv --tb=long
```

### 4. Get Diagnostics

Use diagnostic tools to understand what's happening:

```bash
# Diagnose selftest harness vs service issues
make selftest-doctor

# Get verbose AC freshness output
make check-ac-freshness-verbose

# Show selftest plan without running it
uv run swarm/tools/selftest.py --plan

# Run selftest in degraded mode (skip non-blocking checks)
make selftest-degraded
```

---

## Exit Code Meanings

The CI system uses standard Unix exit codes. Understand what each means:

| Exit Code | Meaning | CI Behavior | Next Steps |
|-----------|---------|-------------|-----------|
| **0** | All checks passed | Merge allowed | None; all good |
| **1** | Validation or test failure | Merge blocked | Review failure, fix code, push again |
| **2** | Fatal error (environment issue, not code) | Merge blocked | Check environment (missing files, bad lockfile, etc.) |

**Examples:**

```bash
# Exit 0: All clear
$ make validate-swarm
✓ All validation checks passed
$ echo $?
0

# Exit 1: Validation failed (fixable)
$ make validate-swarm
✗ Agent 'foo-bar' has color 'blue' but role family 'spec' expects 'purple'
$ echo $?
1

# Exit 2: Fatal error (environment problem)
$ uv run pytest
fatal: python not found
$ echo $?
2
```

---

## Common Failures and Solutions

### "pytest not found" / "ModuleNotFoundError"

**Symptom:**
```
ModuleNotFoundError: No module named 'pytest'
```

**Cause:** Dependencies are not installed.

**Solution:**
```bash
# Sync dependencies with dev extras
uv sync --frozen --extra dev

# Verify pytest is available
uv run pytest --version
```

---

### "AC matrix out of sync"

**Symptom:**
```
✗ AC FRESHNESS: AC matrix in docs/SELFTEST_AC_MATRIX.md is out of sync with implementation
```

**Cause:** The AC matrix documentation doesn't match the actual acceptance criteria in the code.

**Solution:**

1. Check what changed:
   ```bash
   make check-ac-freshness-verbose
   ```

2. Review the differences between spec and implementation

3. Update the AC matrix to match implementation:
   ```bash
   # Regenerate the matrix (if you have a tool for it)
   # or manually edit docs/SELFTEST_AC_MATRIX.md
   $EDITOR docs/SELFTEST_AC_MATRIX.md
   ```

4. Verify the fix:
   ```bash
   make check-ac-freshness
   ```

---

### "Degradation schema mismatch"

**Symptom:**
```
test_selftest_degradation_schema_compliance.py::test_degradation_schema FAILED
AssertionError: Expected field 'reason' in degradation entry, got: ...
```

**Cause:** A degradation entry in the degradation log doesn't match the expected schema.

**Solution:**

1. Check the degradation log:
   ```bash
   # Show current degradations
   uv run swarm/tools/show_selftest_degradations.py
   ```

2. Review the failing test to understand the schema:
   ```bash
   uv run pytest tests/test_selftest_degradation_schema_compliance.py -vv
   ```

3. Fix the degradation entry in the degradation log file (usually `swarm/runs/<run-id>/degradations.json`)

4. Re-run the test:
   ```bash
   uv run pytest tests/test_selftest_degradation_schema_compliance.py -v
   ```

---

### "Git history too shallow"

**Symptom:**
```
✗ AC FRESHNESS: Cannot check freshness; git history is too shallow
  (need full history, got depth 1)
```

**Cause:** CI cloned with `fetch-depth: 1` (shallow), but AC freshness check needs full history.

**Solution:**

In your CI workflow, ensure `fetch-depth: 0` (full history):

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history for AC freshness checks
```

---

### "validator-failed" / Swarm spec validation error

**Symptom:**
```
✗ BIJECTION: swarm/AGENTS.md:line 42: Agent 'foo-bar' is registered but
  .claude/agents/foo-bar.md does not exist
```

**Cause:** Agent registry and agent files are out of sync.

**Solution:**

1. Check what's wrong:
   ```bash
   make validate-swarm
   # or for machine-readable output:
   uv run swarm/tools/validate_swarm.py --json | jq '.summary'
   ```

2. Fix the issue (examples):
   - **Missing agent file**: Create `.claude/agents/<key>.md` or remove from registry
   - **Color mismatch**: Update `color:` in agent frontmatter to match role family
   - **Bad YAML**: Check frontmatter syntax (make sure `---` markers are correct)

3. Verify the fix:
   ```bash
   make validate-swarm
   ```

---

### "Tests pass locally but fail in CI"

**Symptom:** Your local `uv run pytest` passes, but `test-swarm` job fails in CI.

**Diagnosis:**

This usually means:
1. Different Python version locally vs CI (check `python --version`)
2. Different dependency versions (run `uv sync --frozen` to match CI lockfile)
3. Different working directory or file paths
4. Timing-dependent flakiness (test passes sometimes, not always)

**Solution:**

```bash
# Replicate CI environment exactly
python --version  # Should be 3.13
uv sync --frozen --extra dev

# Run the same test command as CI
uv run pytest -v --tb=short

# If still failing, check for flakiness
uv run pytest -v --tb=short --count=5  # Run 5 times
```

---

### "Flaky tests" / Intermittent failures

**Symptom:** A test passes sometimes and fails sometimes, no obvious pattern.

**Diagnosis:**

Flaky tests often indicate:
- Race conditions (tests running in parallel)
- File system timing (files not written/read in time)
- Network requests (timeouts, DNS issues)
- Random seed issues (random order of operations)

**Solution:**

```bash
# Run tests sequentially (not in parallel)
uv run pytest -v --tb=short -n0  # Disable parallelization

# Run with fixed random seed
uv run pytest -v --tb=short --random-order-seed=12345

# Run the test multiple times
uv run pytest tests/test_selftest_api_contract.py -v --count=10

# Get diagnostics
make selftest-doctor
```

---

## Cross-PR Failures: When Unrelated PRs Fail

Sometimes a PR fails in CI even though the changes don't touch related code. This section documents known causes and mitigations.

### Vendor SDK Artifacts Stale

**Symptom:**
```
FAIL: docs/vendor/anthropic/agent-sdk/python/VERSION.json is stale
  Vendored: 0.1.5
  Installed: 0.1.6
Run: make vendor-agent-sdk
```

**Cause:** The Claude Agent SDK was updated upstream since vendor artifacts were generated.

**Why it affects unrelated PRs:**
- SDK vendor check runs on all PRs in `test-swarm` job
- For PRs touching SDK-related paths, check is strict (fails CI)
- For unrelated PRs, check emits a warning but doesn't block

**Paths that trigger strict enforcement:**
- `docs/vendor/anthropic/`
- `swarm/tools/vendor_agent_sdk`
- `tests/contract/test_upstream_sdk`

**Solution:**
```bash
# Update vendored artifacts
make vendor-agent-sdk

# Commit the changes
git add docs/vendor/
git commit -m "chore: update vendored SDK artifacts"
```

### TypeScript/JS Drift Detected

**Symptom:**
```
::error::Flow Studio JS drift detected! Run 'make ts-build' and commit the output.
```

**Cause:** Compiled JavaScript files don't match TypeScript sources.

**Why it happens:**
- TypeScript was edited but JS not recompiled
- Different tsc version produces different output
- Build artifacts were modified directly

**Solution:**
```bash
# Rebuild TypeScript
cd swarm/tools/flow_studio_ui && npm run ts-build

# Commit the compiled output
git add swarm/tools/flow_studio_ui/js/
git commit -m "build: regenerate Flow Studio JS"
```

### HTML Generation Drift

**Symptom:**
```
test_flow_studio_html_migration.py::test_backends_serve_identical_html FAILED
```

**Cause:** Generated `index.html` doesn't match fragment sources.

**Solution:**
```bash
# Regenerate HTML from fragments
make gen-index-html

# Verify the fix
uv run pytest tests/test_flow_studio_html_migration.py -v
```

### OpenAPI Schema Changes

**Symptom:**
```
test_flow_studio_schema_stability.py::test_required_endpoints_still_documented FAILED
```

**Cause:** FastAPI endpoints changed without updating the baseline schema.

**Solution:**
```bash
# Dump new schema baseline
make dump-openapi-schema

# Review changes to ensure no unintended breaking changes
git diff docs/flowstudio-openapi.json

# Commit if changes are intentional
git add docs/flowstudio-openapi.json
git commit -m "docs: update OpenAPI schema baseline"
```

### Guardrail Test Philosophy

Flow Studio uses guardrail tests to prevent drift between sources and artifacts:

| Artifact | Source | Check Command | Regenerate Command |
|----------|--------|---------------|-------------------|
| Agent frontmatter | `swarm/config/agents/*.yaml` | `make check-adapters` | `make gen-adapters` |
| Flow diagrams | `swarm/config/flows/*.yaml` | `make check-flows` | `make gen-flows` |
| TypeScript constants | `swarm/config/flows.yaml` | `make check-flow-constants` | `make gen-flow-constants` |
| index.html | `fragments/*.html` | `make check-index-html` | `make gen-index-html` |
| Compiled JS | `src/**/*.ts` | `check-ui-drift` job | `npm run ts-build` |
| OpenAPI schema | FastAPI app | N/A | `make dump-openapi-schema` |
| Vendor SDK | Installed SDK | `make check-vendor-agent-sdk` | `make vendor-agent-sdk` |

**When a guardrail test fails:**
1. Check if the failure is in CI but not local (sync environment first)
2. Regenerate the artifact from its source
3. Review the diff to ensure changes are expected
4. Commit the regenerated artifact

---

## Pre-flight Checks: What CI Validates

Before any test runs, CI validates the environment. Understanding these checks helps you debug setup issues:

### Required Files Exist

CI expects these files to be present:

```bash
# Check for required files
test -f uv.lock          # Python dependency lockfile
test -f pyproject.toml   # Python project metadata
test -f Makefile         # Build targets
test -d .github/workflows/  # CI workflows
test -d swarm/           # Swarm framework
test -d .claude/         # Agent and skill definitions
```

If any are missing, you'll see exit code 2 (fatal).

**Fix:**
```bash
# Regenerate missing files if they were deleted
git checkout uv.lock pyproject.toml Makefile
```

### pytest Can Discover Tests

CI runs `uv run pytest` without specifying test files, so pytest must auto-discover them:

```bash
# Check that pytest can find tests
uv run pytest --collect-only

# If discovery fails, check:
# - All test files are named test_*.py or *_test.py
# - All test functions are named test_*()
# - __init__.py files exist in test directories (if needed)
```

### Git History Depth Is Sufficient

AC freshness checks need full git history:

```bash
# Check git history depth
git log --oneline | wc -l

# If depth is 1, you have a shallow clone
# Fix with: git fetch --unshallow
git fetch --unshallow
```

### uv Dependencies Are Locked

CI uses `uv sync --frozen`, which requires an up-to-date lockfile:

```bash
# Check if lockfile is current
uv lock --check

# If not, regenerate
uv lock
```

---

## Diagnostic Tools and Commands

When things go wrong, use these tools to understand why:

### selftest-doctor: Diagnose Harness vs Service Issues

Separates environmental/harness problems from actual code failures:

```bash
make selftest-doctor
```

**Output explains:**
- HARNESS_ISSUE: Infrastructure problem (Python, uv, git, etc.)
- SERVICE_ISSUE: Code or test failure
- UNKNOWN: Couldn't determine the type

**Example output:**
```
Diagnostic Report
=================
Status: HARNESS_ISSUE
Reason: uv not found in PATH
Action: Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Verbose AC Freshness Check

Get detailed output on AC matrix alignment:

```bash
make check-ac-freshness-verbose
```

**Shows:**
- Which ACs are in the matrix
- Which ACs are in the implementation
- Specific mismatches with line numbers

### Selftest Plan (No Execution)

See what will run without actually running it:

```bash
uv run swarm/tools/selftest.py --plan
```

**Output shows:**
- All 16 steps
- Which tier each belongs to (KERNEL, GOVERNANCE, OPTIONAL)
- Dependencies between steps
- Estimated runtime

### Selftest with JSON Output

Get machine-readable diagnostics:

```bash
uv run swarm/tools/selftest.py --json | jq '.summary'
```

**Shows:**
- Exit code
- Which steps passed/failed
- Detailed failure reasons with fix suggestions

### Validation in JSON Mode

Machine-readable validation output for tools/dashboards:

```bash
uv run swarm/tools/validate_swarm.py --json | jq '.summary'
```

---

## When to Ask for Help

If you've tried the above and the issue persists, here's how to get help and what information to include:

### Issue Only Happens in CI (Not Locally)

**Checklist:**
- [ ] Run `uv sync --frozen` locally (match CI's lockfile)
- [ ] Verify `python --version` is 3.13+
- [ ] Check `git log --oneline | wc -l` is > 1 (full history)
- [ ] Run the exact CI command: `make dev-check`

**Information to include when asking for help:**
```bash
# Capture environment info
python --version
uv --version
git log --oneline | wc -l
uv run pytest --version

# Capture the failure
make dev-check 2>&1 | tee ci-failure.log

# Capture diagnostics
make selftest-doctor > diagnostics.txt 2>&1

# Share the logs and diagnostics
```

### Exit Code 2 (Fatal Error, Not Code Issue)

Exit code 2 means the test harness itself has a problem, not your code.

**Likely causes:**
- Python not installed or wrong version
- uv not in PATH
- Required file missing (uv.lock, pyproject.toml)
- Git repository corrupted
- Disk full or permission denied

**How to debug:**
```bash
# Check Python
python --version  # Should be 3.13+
which python

# Check uv
which uv
uv --version

# Check required files
ls -la uv.lock pyproject.toml

# Check disk space
df -h

# Check git
git log -1 --oneline
git status
```

### Flaky Tests That Fail Intermittently

Save diagnostics for the next failure:

```bash
# Run test in a loop and capture first failure
for i in {1..20}; do
  echo "Run $i..."
  uv run pytest tests/test_selftest_api_contract.py -v || {
    echo "FAILED on run $i"
    make selftest-doctor > diagnostics-run-$i.txt
    break
  }
done
```

**Information to include:**
- How many times does it fail? (1/10 runs? 3/20 runs?)
- Is there a pattern? (fails when run after other tests? always on main branch?)
- Any recent changes to test files or dependencies?

---

## Troubleshooting Flowchart

```
Does make dev-check pass locally?
│
├─ YES → Issue only happens in CI
│        └─ Check environment differences:
│           • Python version (python --version)
│           • uv version (uv --version)
│           • Git history (git log | wc -l)
│           • Run: uv sync --frozen
│
└─ NO → Issue happens locally
         │
         └─ What's the exit code?
            │
            ├─ Exit 0 (passed) → Intermittent/flaky
            │  └─ Run 5 times: make dev-check && make dev-check && ...
            │
            ├─ Exit 1 (test failure) → Reproducible failure
            │  └─ Isolate which step:
            │     • make validate-swarm
            │     • make selftest-doctor
            │     • uv run pytest tests/test_*.py -v
            │
            └─ Exit 2 (fatal error) → Environment problem
               └─ Check:
                  • python --version (need 3.13+)
                  • which uv (need in PATH)
                  • ls -la uv.lock (must exist)
                  • git log (full history needed)
```

---

## Common GitHub Actions Failures and Fixes

These failures are specific to GitHub Actions CI environment:

### "python not found" in CI

**Cause:** Python version not set up correctly in workflow.

**Fix:** Ensure workflow has setup-python step:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.13"
```

### "uv: command not found" in CI

**Cause:** uv not installed or not in PATH.

**Fix:** Ensure workflow installs uv:

```yaml
- name: Install uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Workflow times out

**Cause:** A step runs too long (default 6 hours, jobs can set shorter timeouts).

**Check the workflow file for timeout-minutes:**

```yaml
jobs:
  validate-swarm:
    timeout-minutes: 5  # 5 minute timeout
```

**Fix:** Either optimize the step or increase timeout (if reasonable).

### Shallow clone breaks AC freshness

**Cause:** Checkout uses `fetch-depth: 1` but AC freshness needs full history.

**Fix:** Use `fetch-depth: 0`:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history
```

---

## Workflow Files Reference

For quick lookup, here are the three main CI workflows:

| Workflow | File | Runs On | Purpose |
|----------|------|---------|---------|
| **Basic CI** | `.github/workflows/ci.yml` | Every push/PR | Validates swarm spec, runs Python tests |
| **Swarm Validation** | `.github/workflows/swarm-validate.yml` | Changes to `swarm/` or `.claude/` | Strict validation on main, lenient on PRs |
| **Selftest Governance Gate** | `.github/workflows/selftest-governance-gate.yml` | Changes to selftest infra | AC matrix, AC tests, degradation tests |

**View workflow status:**

```bash
# List all workflows
gh workflow list

# Check status of a specific workflow
gh workflow view selftest-governance-gate.yml

# View last run
gh run list --workflow=ci.yml

# View specific run details
gh run view <run-id>
```

---

## Quick Command Reference

For easy copy-paste:

```bash
# Reproduce CI locally
uv sync --frozen
make dev-check

# Diagnose issues
make selftest-doctor
make check-ac-freshness-verbose

# Run specific test suites
uv run pytest tests/test_selftest_ac_bijection.py -v
uv run pytest tests/test_selftest_degradation_schema_compliance.py -v

# Get machine-readable output
uv run swarm/tools/validate_swarm.py --json | jq '.summary'
uv run swarm/tools/selftest.py --json | jq '.summary'

# Check environment
python --version
uv --version
git log --oneline | wc -l
```

---

## Need More Help?

- **Selftest system docs**: See `docs/SELFTEST_SYSTEM.md` for deep technical details
- **Selftest governance**: See `docs/SELFTEST_GOVERNANCE.md` for escalation tree and remediation
- **Swarm architecture**: See `CLAUDE.md` for overview of flows, agents, and philosophy
- **GitHub Actions docs**: https://docs.github.com/en/actions
