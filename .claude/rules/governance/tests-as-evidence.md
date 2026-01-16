# Tests As Evidence

Tests are evidence only if they would fail when the requirement isn't met.

## What Makes Tests Trustworthy
| Check | Purpose |
|-------|---------|
| **Mutation testing** | Tests that don't catch mutations are hollow |
| **Coverage with assertions** | Executed ≠ tested |
| **Failure modes tested** | Happy path only = incomplete |
| **BDD traceability** | Specs trace to tests |

## Evidence in Receipts
```json
{
  "tests": { "measured": true, "passed": 42, "evidence": "test_output.log" },
  "coverage": { "measured": true, "line_percent": 87 },
  "mutation": { "measured": true, "score_percent": 78 }
}
```

If not measured, say so: `"measured": false, "reason": "..."`

## The Rule
- If you can't point to a test that would fail, requirement isn't tested
- "Tests pass" without proof of effectiveness is narrative, not physics
- Never evaluate on single metric (use panels)

> Docs: docs/governance/TESTS_AS_EVIDENCE.md
