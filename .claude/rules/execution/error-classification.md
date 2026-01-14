# Error Classification

Errors are routing signals, not hard stops. This document defines error categories and their detection criteria.

## The Fix-Forward Principle

**Errors are information, not barriers.**

The system's job is to complete flows with documented issues, not to halt at the first problem. Every error becomes a routing decision:
- Retry? (transient)
- Fail fast? (permanent)
- Try again with limits? (retriable)
- Stop everything? (fatal)

Only fatal errors halt immediately. Everything else routes forward.

## Error Categories

### 1. Transient Errors

**Definition:** Temporary failures caused by external conditions that are likely to resolve on their own.

| Signature | Examples |
|-----------|----------|
| Network failure | `ConnectionError`, `TimeoutError`, `ETIMEDOUT` |
| Rate limiting | HTTP 429, `RateLimitExceeded`, `quota_exceeded` |
| Service unavailable | HTTP 502, 503, 504, `ServiceUnavailable` |
| Resource contention | `EBUSY`, `ResourceTemporarilyUnavailable` |

**Detection Criteria:**
```json
{
  "error_class": "transient",
  "indicators": [
    "exit_code in [124, 137]",
    "http_status in [408, 429, 500, 502, 503, 504]",
    "error_message matches /timeout|timed out|connection refused|rate limit/i"
  ]
}
```

### 2. Permanent Errors

**Definition:** Failures that will not resolve with retry. The operation is fundamentally invalid.

| Signature | Examples |
|-----------|----------|
| Invalid input | `ValidationError`, malformed JSON, missing required field |
| Missing dependency | `ModuleNotFoundError`, `FileNotFoundError` (for required files) |
| Permission denied | `EACCES`, HTTP 401, 403 |
| Resource not found | HTTP 404, `KeyError` on required config |
| Configuration error | Invalid API key format, malformed YAML |

**Detection Criteria:**
```json
{
  "error_class": "permanent",
  "indicators": [
    "http_status in [400, 401, 403, 404, 422]",
    "error_message matches /invalid|not found|permission denied|unauthorized/i",
    "validation_errors is not empty"
  ]
}
```

### 3. Retriable Errors

**Definition:** Failures that might succeed on retry, but with limits. Often caused by flaky tests, transient lint issues, or non-deterministic operations.

| Signature | Examples |
|-----------|----------|
| Flaky test | Test fails, then passes on rerun |
| Transient lint | Race condition in linter |
| Network glitch | Single packet loss, not sustained |
| Resource race | File locked temporarily |

**Detection Criteria:**
```json
{
  "error_class": "retriable",
  "indicators": [
    "test_failure AND same_test_passed_recently",
    "lint_error AND previous_run_clean",
    "error_message matches /flaky|intermittent|race/i",
    "failure_count < 3 for same signature"
  ]
}
```

### 4. Fatal Errors

**Definition:** Errors that require immediate halt. Continuing would cause harm, data loss, or security breach.

| Signature | Examples |
|-----------|----------|
| Secrets exposure | API key in diff, password in log |
| Data corruption | Incomplete transaction, corrupted file |
| Security breach | Unauthorized access attempt, injection detected |
| Invariant violation | Core assumption broken, state machine invalid |
| Boundary violation | Force push to protected, secrets in commit |

**Detection Criteria:**
```json
{
  "error_class": "fatal",
  "indicators": [
    "secrets_detected in diff or output",
    "data_integrity_check failed",
    "security_scan.critical > 0",
    "invariant_violated",
    "boundary_violation_type is not null"
  ]
}
```

## Quick Reference

| Category | Retry? | Routing | Examples |
|----------|--------|---------|----------|
| Transient | Yes (with backoff) | DETOUR or ESCALATE after exhausted | Rate limit, timeout |
| Permanent | No | BLOCKED or ESCALATE | Validation error, 404 |
| Retriable | Yes (limited) | DETOUR or CONTINUE with warning | Flaky test, race condition |
| Fatal | No | TERMINATE | Secrets leaked, data corruption |

## The Rule

> Errors are routing signals, not hard stops.
> Classify first, then handle according to category.
> When in doubt, advance with documented concerns.

---

## See Also
- [error-handling.md](./error-handling.md) - Handling strategies per category
- [error-aggregation.md](./error-aggregation.md) - Multiple error resolution
- [routing-decisions.md](./routing-decisions.md) - Decision vocabulary
- [fix-forward-vocabulary.md](../governance/fix-forward-vocabulary.md) - BLOCKED is rare
