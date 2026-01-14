# Calibration Loop: The Learning Feedback System

The system should be smarter on Friday than Monday. Automatically.

## The Learning Loop

```
       Runs
        │
        ▼
┌───────────────────┐
│  Flow 7 (Wisdom)  │
│  Extract Signals  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Pattern Detection │
│  (3+ = pattern)   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Propose Change   │
│  (prompt/flow/    │
│   agent)          │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Test Against     │
│  Historical Runs  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Deploy with      │
│  Monitoring       │
└───────────────────┘
```

## Flow 7 (Wisdom) Responsibilities

Flow 7 closes the learning loop by analyzing completed runs:

| Input | Analysis | Output |
|-------|----------|--------|
| Completed runs | What worked, what didn't | Learnings summary |
| Failure patterns | Root cause clustering | Prompt improvement proposals |
| Recurring detours | Pattern frequency | Flow modification proposals |
| Escaped bugs | Where verification failed | Gap analysis |

## Failure Patterns → Prompt Improvements

When the same failure occurs 3+ times:

```json
{
  "pattern_id": "missing-error-handling",
  "occurrences": [
    { "run_id": "run-001", "step": "build-step-3", "description": "No try/catch" },
    { "run_id": "run-005", "step": "build-step-3", "description": "Missing error boundary" },
    { "run_id": "run-008", "step": "build-step-3", "description": "Unhandled exception" }
  ],
  "root_cause": "code-implementer prompt lacks explicit error handling requirement",
  "proposed_fix": {
    "type": "prompt_update",
    "target": "code-implementer",
    "change": "Add explicit requirement: 'All functions that can fail MUST have error handling'"
  }
}
```

## Recurring Detours → Flow Modifications

When the same detour fires frequently:

```json
{
  "pattern_id": "frequent-lint-detour",
  "detour_type": "lint-fix",
  "frequency": "15 of last 20 runs",
  "proposal": {
    "type": "flow_modification",
    "change": "Add lint-check step before code-critic",
    "rationale": "Pre-emptive linting reduces 75% of detours"
  }
}
```

## Escaped Bugs → Verification Gaps

When bugs reach production:

```json
{
  "escaped_bug": {
    "description": "Null reference in user lookup",
    "detected_at": "production",
    "should_have_caught": "gate"
  },
  "gap_analysis": {
    "tests": "No null case in test suite",
    "coverage": "Line covered but branch not tested",
    "recommendation": "Add branch coverage requirement to gate"
  }
}
```

## The Rule

> The learning loop is automatic: signals → patterns → proposals → tests → deploy.
> Flow 7 extracts; pattern detection identifies; testing validates; monitoring confirms.

---

## See Also
- [calibration-signals.md](./calibration-signals.md) - Metrics and signal collection
- [calibration-improvement.md](./calibration-improvement.md) - Pattern detection and improvement process
- [flow-charters.md](./flow-charters.md) - Flow 7 (Wisdom) charter
- [detour-catalog.md](../execution/detour-catalog.md) - Known fix patterns
