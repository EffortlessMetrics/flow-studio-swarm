# Test Anti-Patterns

## Purpose

Identify tests that provide false confidence. Anti-patterns undermine the evidence value of tests.

## The Rule

> Tests that don't catch mutations are hollow.
> When in doubt, add tests. Never add manual review.
> Doubt escalates to tests, not to humans.

## Anti-Patterns

### Coverage Gaming

```python
# ANTI-PATTERN: Execute without assert
def test_all_paths():
    for input in all_inputs:
        function(input)  # 100% coverage, 0% verification
```

**Problem**: Counts as coverage but proves nothing.

### Trivial Tests

```python
# ANTI-PATTERN: Testing language features
def test_getter():
    user = User(name="Alice")
    assert user.name == "Alice"  # Tests Python, not your code
```

**Problem**: Passes regardless of business logic correctness.

### Flaky Tests

```python
# ANTI-PATTERN: Non-deterministic test
def test_timing():
    start = time.time()
    slow_operation()
    assert time.time() - start < 1.0  # Fails randomly
```

**Problem**: Non-deterministic tests are not evidence. They're noise.

### Test Rot

```python
# ANTI-PATTERN: Test passes but doesn't reflect behavior
def test_old_behavior():
    # This test was written for v1
    # Code is now v3
    # Test still passes but tests nothing relevant
    assert True
```

**Problem**: Tests that pass regardless of current behavior are false confidence.

## Verification Escalation

When in doubt, add tests. Never add manual review.

| Signal | Response |
|--------|----------|
| "I think it works" | Add test that proves it |
| "Edge case might fail" | Add test for that edge case |
| "Not sure about concurrent access" | Add concurrency test |
| "Reviewer should check" | Wrong. Add test. |

### Escalation Ladder

1. **Unit tests** - Fast, isolated, deterministic
2. **Integration tests** - Boundary verification
3. **Mutation testing** - Test effectiveness
4. **Fuzz testing** - Edge case discovery
5. **Property-based testing** - Invariant verification

## Quality Signals

### Mutation Score

Mutation score measures test effectiveness:

| Score | Meaning | Action |
|-------|---------|--------|
| 90%+ | Tests catch most changes | Good coverage |
| 70-90% | Some blind spots | Review surviving mutants |
| < 70% | Tests are weak | Major test gaps |

### Assertion Density

Assertions per test indicate thoroughness:

| Density | Meaning |
|---------|---------|
| 0 assertions | Hollow test (not evidence) |
| 1 assertion | Minimal verification |
| 3-5 assertions | Thorough verification |
| 10+ assertions | Consider splitting test |

## Detection Checklist

| Anti-Pattern | Detection | Fix |
|--------------|-----------|-----|
| Coverage gaming | High coverage + low mutation score | Add assertions |
| Trivial tests | Tests for getters/setters only | Test business logic |
| Flaky tests | Random CI failures | Remove time/network dependencies |
| Test rot | Tests unchanged as code evolves | Audit test relevance |

---

## See Also

- [tests-as-evidence.md](./tests-as-evidence.md) - What makes tests trustworthy
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
- [panel-thinking.md](./panel-thinking.md) - Multi-metric evaluation
