# Error Aggregation

When multiple errors occur, which wins?

## Precedence (highest wins)
1. FATAL → Always wins. Halt immediately.
2. PERMANENT → Cannot proceed. Block or escalate.
3. RETRIABLE → Try again with limits.
4. TRANSIENT → Retry with backoff.

## Same-Category Aggregation
- Fatal: First fatal wins (stop immediately)
- Permanent: Collect all, use highest severity
- Retriable: Track signatures, retry if any might succeed
- Transient: Use longest backoff, retry once

## The Rule
- Fatal wins. Permanent blocks. Retriable yields. Transient waits.
- When aggregating, highest category determines outcome.
- Lower-category errors are suppressed but logged.

> Docs: docs/execution/ERROR_TAXONOMY.md
