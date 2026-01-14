# Evidence Anti-Patterns

Mistakes in how evidence is captured, validated, and evaluated.

## Hollow Tests

**Pattern:** Tests that execute but don't assert.

```python
def test_user_creation():
    user = create_user("test@example.com")
    # Look ma, no assertions!
```

**Why it's wrong:** Coverage says 100%. Mutation testing says 0%. These tests verify the code runs without crashing—not that it produces correct results. This is panel disagreement.

**What to do instead:** Require meaningful assertions.
```python
def test_user_creation():
    user = create_user("test@example.com")
    assert user.email == "test@example.com"
    assert user.id is not None
    assert user.created_at is not None
```

**The rule:** If a test has no assertions, it's not a test. Use panels (coverage + mutation) to catch hollow tests.

---

## Stale Receipts

**Pattern:** Evidence from old commits.

```
Evidence: Tests passed (from 3 commits ago)
Current commit: 5 files changed
```

**Why it's wrong:** The evidence doesn't prove the current state. Stale receipts are invalid. If files changed, evidence must be regenerated.

**What to do instead:** Bind evidence to commit SHA.
```json
{
  "tests": {
    "passed": 47,
    "commit_sha": "abc123",
    "fresh": true
  }
}
```

**The rule:** Evidence must be fresh. Same commit or it's unverified.

---

## Single Metric

**Pattern:** Trusting one number.

```
"Coverage is 90%, ship it!"
*tests are hollow, security scan not run*
```

**Why it's wrong:** Single metrics get gamed. High coverage + hollow tests = false confidence. Panels resist gaming—multiple metrics that should agree.

**What to do instead:** Use panels of evidence.
```
Quality Panel:
- Tests: 47 passed
- Coverage: 90%
- Mutation: 85% killed (tests are real)
- Lint: 0 errors
- Security: 0 vulnerabilities
```

**The rule:** Never evaluate on a single metric. Panel disagreement reveals problems.

---

## Narrative Substitution

**Pattern:** "Tests passed" without captured output.

```
Agent: "All tests passed successfully"
Evidence: (none)
```

**Why it's wrong:** This is the most common form of narrative trust. The claim exists. The evidence doesn't. This is testimony, not proof.

**What to do instead:** Capture tool output.
```json
{
  "tests": {
    "measured": true,
    "command": "pytest tests/ -v",
    "passed": 47,
    "failed": 0,
    "evidence_path": "RUN_BASE/build/test_output.log"
  }
}
```

**The rule:** Claims require evidence pointers. No path, no proof.

---

## See Also
- [anti-patterns-index.md](./anti-patterns-index.md) - Full quick reference
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
- [truth-hierarchy.md](./truth-hierarchy.md) - Evidence levels
- [panel-thinking.md](./panel-thinking.md) - Multi-metric verification
- [testing-philosophy.md](./testing-philosophy.md) - Tests as evidence
