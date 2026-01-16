# Retry Policy

Retries handle transient failures only.

## By Category
| Category | Strategy | Max |
|----------|----------|-----|
| Transient | Exponential backoff + jitter | 5 |
| Permanent | Fail fast | 0 |
| Retriable | Limited, no backoff | 3 |
| Fatal | Halt immediately | 0 |

## No Retry (Permanent)
- HTTP 400, 401, 403, 404, 422
- ValidationError, AuthenticationError

## Rate Limits (429)
Respect `Retry-After` header. Cap at 300s.

> Docs: docs/execution/ERROR_HANDLING.md
