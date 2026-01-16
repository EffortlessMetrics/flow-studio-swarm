# Test Anti-Patterns

Tests that don't catch mutations are hollow.

## Anti-Patterns

- **Coverage gaming**: Execute without assert = not evidence
- **Trivial tests**: Testing language features = noise
- **Flaky tests**: Non-deterministic = noise
- **Implementation tests**: Testing internals = brittle

## Detection

High coverage + low mutation score = weak tests.

## Rules

- When in doubt, add tests
- Never add manual review where automated test would work
- Tests should fail when requirements are not met
