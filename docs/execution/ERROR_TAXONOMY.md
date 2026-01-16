# Error Taxonomy

Errors are routing signals, not hard stops.

## Categories

| Category | Description | Examples |
|----------|-------------|----------|
| Transient | Temporary, will resolve | Network timeout, rate limit, 5xx |
| Permanent | Won't resolve with retry | Validation error, 404, permission denied |
| Retriable | Might succeed, with limits | Flaky test, race condition |
| Fatal | Must halt, danger | Secrets leaked, data corruption |

## Detection Signals

- Transient: exit codes 124/137, HTTP 429/500/502/503
- Permanent: HTTP 400/401/403/404/422, ValidationError
- Retriable: test failure + same test passed recently
- Fatal: secrets in output, integrity check failed

## Aggregation Precedence

FATAL > PERMANENT > RETRIABLE > TRANSIENT

Highest category determines outcome.
