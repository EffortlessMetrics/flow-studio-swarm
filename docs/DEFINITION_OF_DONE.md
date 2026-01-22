# Definition of Done (v3.0.0-rc.1)

> **Purpose:** This document defines what "done" means for merging code into Flow Studio.
> It consolidates the three CI gates, validation rules, and quality expectations.

## Current Baseline (v3.0.0-rc.1)

| Metric | Value |
|--------|-------|
| Tests Passed | ~1750 |
| Tests Skipped | 41 (env-gated) |
| Tests XFailed | 0 |
| Warnings | 0 |

Any new xfail or warning must be justified and documented in release notes.

---

## Executive Summary

A PR is "done" when it passes **three mandatory CI gates** and follows the **quality standards** defined below. This is enforced automatically via GitHub Actions.

| Gate | Job Name | Purpose | Local Command |
|------|----------|---------|---------------|
| 1 | `validate-swarm` | Spec alignment | `make validate-swarm` |
| 2 | `test-swarm` | Tests pass | `uv run pytest tests/` |
| 3 | `selftest-governance-gate` | Governance | `make selftest` |

All three gates must pass before merge.

---

## Gate 1: Swarm Spec Alignment (validate-swarm)

This gate ensures the swarm specification (flows, agents, skills) is internally consistent.

### Validation Rules (FR-001 through FR-005)

| Rule | Description | What it Checks |
|------|-------------|----------------|
| **FR-001** | Agent Registry Bijection | Every agent in `swarm/AGENTS.md` has a file in `.claude/agents/`, and vice versa |
| **FR-002** | Frontmatter Validation | Agent files have valid YAML frontmatter with required fields (name, description, model) |
| **FR-003** | Flow References | All agents referenced in flow specs exist in the registry |
| **FR-004** | Skills Validation | Skill declarations in agent frontmatter reference valid skill files |
| **FR-005** | RUN_BASE Paths | Path references in prompts use `RUN_BASE/` convention, not hardcoded paths |

### How to Run Locally

```bash
make validate-swarm              # Standard validation
make validate-swarm-strict       # Strict mode (warnings are errors)
uv run swarm/tools/validate_swarm.py --json  # Machine-readable output
```

### If Gate 1 Fails

1. Read the error message - it includes file path and specific issue
2. Run `make validate-swarm` locally to reproduce
3. Fix the misalignment (usually: sync AGENTS.md with .claude/agents/)
4. Re-run validation before pushing

---

## Gate 2: Test Suite (test-swarm)

This gate ensures all unit and integration tests pass.

### Test Requirements

- **All tests must pass** - no exceptions
- **No new flaky tests** - tests must be deterministic
- **Coverage maintained** - no significant coverage drops

### Test Categories

| Category | Marker | Description | Gating? |
|----------|--------|-------------|---------|
| Unit | `@pytest.mark.unit` | Fast, isolated tests | Yes |
| Integration | `@pytest.mark.integration` | Cross-component tests | Yes |
| Slow | `@pytest.mark.slow` | Tests taking >5s | Yes |
| BDD | `@pytest.mark.bdd` | Gherkin scenario tests | Yes |
| Performance | `@pytest.mark.performance` | Benchmark tests | **No** |

**Note:** Performance tests are non-gating because they are hardware-dependent. Run them locally with `make test-performance`.

### How to Run Locally

```bash
uv run pytest tests/                    # Full suite
uv run pytest tests/ -m unit            # Unit tests only
uv run pytest tests/ -m "not slow"      # Skip slow tests
uv run pytest tests/ -v --tb=short      # Verbose with short traceback
```

### If Gate 2 Fails

1. Run `uv run pytest tests/ -v --tb=short` locally
2. Fix failing tests
3. If a test is genuinely flaky, mark it with `@pytest.mark.skip(reason="Flaky: <issue-link>")`
4. Never mark a test as xfail without a documented reason

---

## Gate 3: Governance Enforcement (selftest-governance-gate)

This gate ensures the selftest system and acceptance criteria are maintained.

### What It Checks

| Check | Description |
|-------|-------------|
| **AC Matrix Freshness** | Acceptance criteria aligned across Gherkin, docs, and code |
| **AC Test Suite** | Bijection tests, API contracts, traceability |
| **Degradation Tracking** | Selftest degradation schema is valid |
| **Step Count Invariants** | 16 steps (1 KERNEL + 13 GOVERNANCE + 2 OPTIONAL) |

### How to Run Locally

```bash
make selftest                 # Full 16-step suite
make selftest-doctor          # Diagnose issues
make kernel-smoke             # Fast kernel check (~300ms)
```

### If Gate 3 Fails

1. Run `make selftest-doctor` to identify the issue
2. Check if step counts changed (update `selftest_config.py` and docs)
3. Check if AC matrix is stale (update `docs/SELFTEST_AC_MATRIX.md`)
4. Re-run `make selftest` before pushing

---

## Quality Standards

### Code Quality

- **Python**: Format with `black`, lint with `ruff`
- **TypeScript**: Type-check with `tsc`, lint with eslint
- **YAML**: 2-space indentation, proper quoting
- **Markdown**: GitHub-flavored, spell-checked

### Documentation

- **New agents**: Must be in `swarm/AGENTS.md` AND `.claude/agents/`
- **New flows**: Must have flow spec in `swarm/flows/` AND command in `.claude/commands/`
- **Breaking changes**: Must update CHANGELOG.md and relevant docs

### Test Expectations

| Status | Meaning | When to Use |
|--------|---------|-------------|
| PASS | Test succeeds | Normal tests |
| SKIP | Test not run | Env-gated (API keys, services) |
| XFAIL | Expected failure | Documented MVP gap |
| XPASS | Unexpected pass | Promote to regular test |

### Adding New xfail Tests

If you must add an xfail test:
1. Use `@pytest.mark.xfail(reason="<reason>", strict=False)`
2. Include a clear reason explaining WHY it's expected to fail
3. Link to a GitHub issue if the feature is planned
4. Do NOT use xfail to hide flaky tests - fix them instead

---

## Pre-Merge Checklist

Before clicking "Merge", verify:

- [ ] All three CI gates pass (green checkmarks)
- [ ] Code has been reviewed by at least one maintainer
- [ ] No new warnings or deprecations introduced
- [ ] Documentation updated if behavior changed
- [ ] CHANGELOG.md updated for user-facing changes

See [MERGE_CHECKLIST.md](./MERGE_CHECKLIST.md) for the full checklist.

---

## Resolved Limitations (v2.3.1)

The following limitations from v2.3.0 have been resolved:

| Feature | Status | Notes |
|---------|--------|-------|
| `--report json/markdown` flags | ✅ Implemented | All 14 reporting tests pass |
| Frontmatter line numbers | ✅ Implemented | Error messages include line numbers |
| Skill YAML content validation | ✅ Implemented | Malformed YAML properly detected |
| Performance tests | ✅ Non-gating | Marked as `@pytest.mark.performance`, excluded from CI |

### Intentionally Skipped Tests

41 tests are skipped due to environment gating (not failures):

| Category | Reason |
|----------|--------|
| Flask backend tests | Archived - FastAPI only |
| Observability backend tests | Requires external services (Datadog, CloudWatch) |
| SDK smoke tests | Requires ANTHROPIC_API_KEY |
| MCP UX spec tests | Requires MCP server configuration |

---

## Post-Merge Flow

After a PR is merged:

1. **Flow 5 (Deploy)**: Code is deployed via CI/CD
2. **Flow 6 (Wisdom)**: Artifacts are analyzed for regressions and learnings
3. **Feedback Loop**: Any issues discovered feed back into new PRs

---

## Troubleshooting

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Gate 1 fails: "Agent not found" | Agent file missing | Create `.claude/agents/<key>.md` |
| Gate 1 fails: "Agent not in registry" | AGENTS.md outdated | Add entry to `swarm/AGENTS.md` |
| Gate 2 fails: "test_X failed" | Test regression | Fix the code or test |
| Gate 3 fails: "Step count mismatch" | Selftest changed | Update `selftest_config.py` |

### Getting Help

- Run `make selftest-doctor` for diagnostics
- Check [CI_TROUBLESHOOTING.md](./CI_TROUBLESHOOTING.md) for CI-specific issues
- Check [VALIDATION_RULES.md](./VALIDATION_RULES.md) for validation details

---

## Related Documents

- [CONTRIBUTING.md](../CONTRIBUTING.md): How to contribute
- [MERGE_CHECKLIST.md](./MERGE_CHECKLIST.md): Pre-merge checklist
- [VALIDATION_RULES.md](./VALIDATION_RULES.md): Detailed validation rules
- [CI_TROUBLESHOOTING.md](./CI_TROUBLESHOOTING.md): CI/CD troubleshooting
- [SELFTEST_SYSTEM.md](../swarm/SELFTEST_SYSTEM.md): Selftest documentation
