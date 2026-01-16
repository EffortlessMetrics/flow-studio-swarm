# Test Anti-Patterns

Tests that don't catch mutations are hollow.

## The Rule
- Coverage gaming (execute without assert) = not evidence
- Trivial tests (testing language features) = noise
- Flaky tests (non-deterministic) = noise
- When in doubt, add tests. Never add manual review.

## Detection
High coverage + low mutation score = weak tests.

> Docs: docs/governance/TEST_ANTI_PATTERNS.md
