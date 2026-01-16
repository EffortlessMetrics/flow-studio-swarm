# Panel Thinking (Anti-Goodhart)

Single metrics get gamed. Use complementary panels.

## Core Idea

Never evaluate on a single metric. Contradictions within a panel reveal problems.

## Quality Panel Example

| Metric | Purpose |
|--------|---------|
| Tests passing | Basic correctness |
| Line coverage | Code exercised |
| Mutation score | Test strength |
| Complexity | Maintainability |

High coverage + low mutation score = weak tests (gaming detected).

## Rules

- Gaming one metric should hurt another in the same panel
- Panel disagreement reveals problems
- Design panels to catch Goodhart's law violations
