# Tests as Evidence

## Purpose

Tests are evidence, not ceremony. A test is evidence only if it would **fail when the requirement isn't met**.

## The Rule

> If you can't point to a test that would fail if the requirement wasn't met, the requirement isn't tested.
> "Tests pass" without proof of effectiveness is narrative, not physics.

## What Makes Tests Trustworthy

### Mutation Testing

Tests that don't catch mutations are hollow.

| Mutation | Test Response | Meaning |
|----------|---------------|---------|
| Delete a line | Test fails | Test catches the behavior |
| Change `>` to `>=` | Test fails | Test catches boundary |
| Flip boolean | Test fails | Test catches logic |
| Return null | Test fails | Test catches error path |
| Any mutation | Test passes | **Test is hollow** |

If mutants survive, tests don't actually verify behavior.

### Coverage with Assertions

Executed code is not tested code.

```python
# BAD: Coverage without assertion
def test_process_order():
    order = create_order()
    process_order(order)  # Executes 100 lines
    # No assertion - what did we verify?

# GOOD: Coverage with assertion
def test_process_order():
    order = create_order()
    result = process_order(order)
    assert result.status == "completed"
    assert result.total == 150.00
    assert len(result.line_items) == 3
```

Every executed path needs an assertion that would fail if behavior changed.

### Failure Modes Tested

Happy path coverage is not coverage.

| Test Type | What It Proves |
|-----------|---------------|
| Happy path only | Code works when everything's right |
| Edge cases | Code handles boundaries |
| Error paths | Code fails gracefully |
| Concurrent cases | Code handles race conditions |

If you only test success, you don't know what failure looks like.

### BDD Scenarios as Test Cases

Specifications should trace directly to tests.

```gherkin
# Spec
Scenario: User cannot withdraw more than balance
  Given a user with balance $100
  When they attempt to withdraw $150
  Then the withdrawal is rejected
  And the balance remains $100
```

```python
# Test that traces to spec
def test_overdraft_rejected():
    """Traces to: User cannot withdraw more than balance"""
    user = create_user(balance=100)
    result = user.withdraw(150)
    assert result.rejected
    assert user.balance == 100
```

Every BDD scenario has a corresponding test. Every test traces to a requirement.

## Evidence in Receipts

Test results in receipts must include:

```json
{
  "tests": {
    "measured": true,
    "passed": 42,
    "failed": 0,
    "skipped": 2,
    "evidence": "RUN_BASE/build/test_output.log"
  },
  "coverage": {
    "measured": true,
    "line_percent": 87,
    "branch_percent": 72,
    "evidence": "RUN_BASE/build/coverage.json"
  },
  "mutation": {
    "measured": true,
    "score_percent": 78,
    "mutants_killed": 156,
    "mutants_survived": 44,
    "evidence": "RUN_BASE/build/mutation_report.html"
  }
}
```

If mutation testing wasn't run, say so:

```json
{
  "mutation": {
    "measured": false,
    "reason": "Mutation testing not configured for this project"
  }
}
```

## The Test Evidence Panel

Never evaluate test quality on a single metric:

| Metric | Purpose | Gaming Risk |
|--------|---------|-------------|
| Pass rate | Basic correctness | Trivial tests |
| Line coverage | Code exercised | Coverage without assertion |
| Branch coverage | Paths exercised | Same as above |
| Mutation score | Test effectiveness | Computationally expensive |
| Assertion count | Verification depth | Verbose tests |

**Panel insight**: High coverage + low mutation score = hollow tests

---

## See Also

- [test-anti-patterns.md](./test-anti-patterns.md) - What makes tests untrustworthy
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
- [panel-thinking.md](./panel-thinking.md) - Multi-metric evaluation
- [truth-hierarchy.md](./truth-hierarchy.md) - Evidence levels
