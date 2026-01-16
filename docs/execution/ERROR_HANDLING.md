# Error Handling

Each error category has a specific handling strategy.

## Strategies by Category

| Category | Strategy | Max Retries |
|----------|----------|-------------|
| Transient | Exponential backoff + jitter | 5 |
| Permanent | Fail fast, capture context | 0 |
| Retriable | Limited retries, no backoff | 3 |
| Fatal | Halt immediately | 0 |

## Circuit Breaker

- CLOSED → 3 failures → OPEN (paused 30s)
- OPEN → 30s → HALF-OPEN (try one)
- HALF-OPEN → success → CLOSED
- 5 total failures → ESCALATE

## Rate Limits (429)

Respect `Retry-After` header. Cap at 300s.

See also: [ERROR_TAXONOMY.md](./ERROR_TAXONOMY.md)
