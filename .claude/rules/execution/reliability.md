# Reliability

Retries handle transient failures. Circuit breakers prevent cascade.

## Retry by Category

| Category | Strategy | Max |
|----------|----------|-----|
| Transient | Exponential backoff + jitter | 5 |
| Retriable | Limited, no backoff | 3 |
| Permanent | Fail fast | 0 |
| Fatal | Halt immediately | 0 |

No retry: HTTP 400, 401, 403, 404, 422. Rate limits (429): respect `Retry-After`, cap at 300s.

## Circuit Breaker

- CLOSED → 3 failures → OPEN (paused 30s)
- OPEN → 30s → HALF-OPEN (try one)
- HALF-OPEN → success → CLOSED; failure → OPEN
- 5 total failures → ESCALATE

## The Rule

- Retries are for transient failures only
- One success resets the breaker
- Give failing services room to recover

> Docs: docs/execution/ERROR_HANDLING.md
