# Retry Policy

Retries handle transient failures. Not all errors deserve retries.

## Retry Decision

For error classification (transient, permanent, retriable, fatal), see [error-taxonomy.md](./error-taxonomy.md).

**Quick reference:**
- Transient errors: Retry with backoff
- Permanent errors: Fail fast, no retry
- Retriable errors: Limited retries, no backoff
- Fatal errors: Halt immediately

## Backoff Strategies

### Exponential Backoff with Jitter

For transient errors (network, rate limits, server errors):

```python
def retry_with_jitter(attempt):
    base_delay = 1.0 * (2 ** attempt)  # 1s, 2s, 4s, 8s...
    jitter = random.uniform(0, 0.5 * base_delay)
    return min(base_delay + jitter, 60)  # Cap at 60s
```

| Attempt | Base Delay | With Jitter (example) |
|---------|------------|----------------------|
| 1 | 1s | 1.0-1.5s |
| 2 | 2s | 2.0-3.0s |
| 3 | 4s | 4.0-6.0s |
| 4 | 8s | 8.0-12.0s |
| 5 | 16s | 16.0-24.0s |

**Why jitter:** Prevents thundering herd when multiple operations retry simultaneously.

### Rate Limit Handling

Rate limits (HTTP 429) get special treatment:

```python
def handle_rate_limit(response):
    retry_after = response.headers.get("Retry-After", 60)
    retry_after = min(int(retry_after), 300)  # Cap at 5 minutes
    sleep(retry_after)
    # Retry with same parameters
```

**Rules:**
- Respect `Retry-After` header when present
- Cap wait at 300 seconds (5 minutes)
- Max 5 retries before escalate
- Log each rate limit event

### No Backoff (Retriable Errors)

For flaky/non-deterministic failures:

```python
def retry_retriable(attempt):
    return attempt < 3  # Just retry immediately, max 3 times
```

No backoff because failures are random, not load-based.

## Retry Limits

| Error Type | Max Retries | Backoff |
|------------|-------------|---------|
| Network timeout | 3 | Exponential |
| 5xx server error | 3 | Exponential |
| Rate limit (429) | 5 | Retry-After header |
| Transient API error | 3 | Exponential |
| Flaky test | 3 | None |
| Resource race | 3 | None |

## No-Retry Errors

These are permanent errors. Retrying wastes resources.

```python
NO_RETRY_CODES = {400, 401, 403, 404, 422}

def should_retry(error):
    if hasattr(error, 'status_code'):
        return error.status_code not in NO_RETRY_CODES
    if isinstance(error, ValidationError):
        return False
    if isinstance(error, AuthenticationError):
        return False
    return True  # Default: try retry
```

| Error Type | Action |
|------------|--------|
| Validation error (400, 422) | Fail immediately |
| Auth error (401, 403) | Escalate |
| Not found (404) | Fail immediately |
| Permanent API error | Escalate |

## The Rule

> Transient errors get retries with backoff.
> Permanent errors fail fast.
> Respect rate limit headers. Cap all delays.

## Implementation Status

| Feature | Status | Location |
|---------|--------|----------|
| Exponential backoff | Designed | Transports implement |
| Rate limit handling | Designed | Transports implement |
| Jitter | Designed | Transports implement |
| No-retry detection | Supported | Error classification |

---

## See Also
- [error-taxonomy.md](./error-taxonomy.md) - Error classification and handling strategies
- [timeout-policy.md](./timeout-policy.md) - Timeout hierarchy
- [circuit-breaker.md](./circuit-breaker.md) - Cascade prevention after repeated failures
