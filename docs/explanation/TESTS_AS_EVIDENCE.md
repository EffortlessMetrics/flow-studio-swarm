# Tests As Evidence

Tests are evidence only if they would fail when the requirement is not met.

## What Makes a Test Evidence

A "tests pass" claim requires:
- **Command** that was run
- **Exit code** captured
- **Output path** (log or summary)
- **Scope**: what the tests cover

## Evidence Binding

```json
{
  "tests": {
    "measured": true,
    "command": "pytest tests/ -v",
    "exit_code": 0,
    "passed": 42,
    "failed": 0,
    "evidence_path": "RUN_BASE/build/test_output.log"
  }
}
```

## Not Measured

If tests were not run:
```json
{
  "tests": {
    "measured": false,
    "reason": "No tests exist for this component"
  }
}
```

This is honest. Assumed pass is dangerous.

## Anti-Patterns

- Coverage without assertions = hollow
- "Tests pass" without captured output = unverified
- Single test run without scope declaration = incomplete

## Rules

- Execute tests and capture evidence
- State NOT MEASURED when appropriate
- Coverage without assertions is not evidence
- Evidence freshness matters (this commit, not last week)

See also: [FORENSICS_OVER_TESTIMONY.md](./FORENSICS_OVER_TESTIMONY.md)
