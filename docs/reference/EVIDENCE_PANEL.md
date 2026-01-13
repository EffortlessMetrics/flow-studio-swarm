# Evidence Panel Reference

This document defines what "panel green" means as a contract. It specifies the
default evidence panel for Flow Studio and risk-tiered extensions.

## Core principle

**Never evaluate on a single metric.** Single metrics get gamed. Panels of
complementary metrics resist gaming because gaming one hurts another.

See `.claude/rules/governance/panel-thinking.md` for the full anti-Goodhart
rationale.

## Default panel (Tier 0)

Every Flow Studio run should produce evidence for these metrics. If a metric
cannot be measured, it must be explicitly marked as `"measured": false` with a
reason.

| Metric | Source | What it proves |
|--------|--------|----------------|
| **Tests** | pytest exit code + captured output | Basic correctness |
| **Lint** | ruff/eslint exit code + captured output | Style and obvious bugs |
| **Secrets scan** | gitleaks patterns on staged diff | No credential leakage |
| **Build** | compile/typecheck if applicable | Code is valid |

### Receipt fields

In step receipts, evidence is captured as:

```json
{
  "tests": {
    "measured": true,
    "passed": 47,
    "failed": 0,
    "evidence_path": "build/test_output.log"
  },
  "lint": {
    "measured": true,
    "errors": 0,
    "warnings": 5,
    "evidence_path": "build/lint_output.log"
  },
  "secrets_scan": {
    "measured": true,
    "findings": 0,
    "evidence_path": "gate/secrets_scan.log"
  }
}
```

If any metric is not measured:

```json
{
  "mutation": {
    "measured": false,
    "reason": "Mutation testing not configured for this project"
  }
}
```

## Risk-tier add-ons

For higher-risk changes, extend the default panel.

### Tier 1: Integration and boundary tests

Add when: Changes touch APIs, external systems, or cross-module boundaries.

| Metric | Source | What it proves |
|--------|--------|----------------|
| Integration tests | pytest markers | Boundaries work correctly |
| Fuzz/property tests | hypothesis/quickcheck | Edge cases handled |
| Type coverage | mypy strict | Type contracts enforced |

### Tier 2: Mutation and deeper analysis

Add when: Changes are security-critical, algorithm-heavy, or core infrastructure.

| Metric | Source | What it proves |
|--------|--------|----------------|
| Mutation score | mutmut/cosmic-ray | Tests actually verify behavior |
| Coverage branches | coverage.py branch | All paths exercised |
| Dependency audit | pip-audit/npm audit | No known vulnerabilities |

## Panel agreement rule

All metrics in a panel should point in the same direction. When they disagree,
investigate before proceeding.

### Agreement examples

| Panel state | Meaning |
|-------------|---------|
| Tests pass, lint clean, secrets clean | Green - proceed |
| Tests pass, lint errors | Amber - fix lint before proceed |
| Tests fail, lint clean | Red - fix tests |
| Tests pass, high coverage, low mutation score | Weak tests - investigate |

### Contradiction signals

Contradictions reveal problems that single metrics miss:

- High coverage + tests passing + low mutation score = hollow tests (execute
  but don't assert)
- Tests passing + lint failing = rushed work (correctness but not quality)
- Fast review time + low evidence count = rubber-stamping

## "Not measured" semantics

Unknown is a first-class state. Silent absence is not.

### Rules

1. If a metric was not measured, say so explicitly: `"measured": false`.
2. Provide a reason: `"reason": "No security scanner configured"`.
3. Reviewer decides if the risk is acceptable.
4. Never guess or omit.

### Example

```json
{
  "mutation": {
    "measured": false,
    "reason": "Mutation testing takes 30+ minutes; skipped for fast iteration"
  }
}
```

This is honest. Pretending mutation testing passed when it didn't run is not.

## Escalation, not manual review

When in doubt, the answer is **more evidence**, not manual code review.

| Signal | Escalation |
|--------|------------|
| "I think it works" | Add test that proves it |
| "Edge case might fail" | Add test for that edge case |
| "Not sure about security" | Run security scanner |
| "Reviewer should check" | Wrong. Add automated check. |

Humans audit evidence. Machines produce evidence. Reversing this wastes human
attention and produces worse outcomes.

## Implementation status

| Component | Status |
|-----------|--------|
| Test evidence in receipts | Implemented |
| Lint evidence in receipts | Implemented |
| Secrets scan at gate | Implemented |
| Mutation testing | Designed (not automated) |
| Fuzz testing | Designed (not automated) |
| Panel contradiction detection | Designed (manual) |

## See also

- `.claude/rules/governance/panel-thinking.md` - Anti-Goodhart rationale
- `.claude/rules/governance/evidence-discipline.md` - What counts as evidence
- `.claude/rules/governance/truth-hierarchy.md` - Evidence levels
- `.claude/rules/governance/reviewer-protocol.md` - How humans review evidence
