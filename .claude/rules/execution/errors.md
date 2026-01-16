# Error Handling

Errors are routing signals, not hard stops.

## Categories

| Category | Behavior | Max Retries |
|----------|----------|-------------|
| **Transient** | Retry with exponential backoff | 5 |
| **Permanent** | Fail fast, capture context | 0 |
| **Retriable** | Limited retries, no backoff | 3 |
| **Fatal** | Halt immediately, preserve state | 0 |

## Precedence (highest wins)

Fatal > Permanent > Retriable > Transient

## The Rule

- Classify first, then handle according to category
- Only fatal errors halt immediately
- Everything else routes forward with documented concerns
- When in doubt, advance with documented concerns

> Docs: docs/execution/ERROR_TAXONOMY.md
