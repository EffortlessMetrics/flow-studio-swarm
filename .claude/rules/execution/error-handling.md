# Error Handling Strategies

Each error category has a specific handling strategy. See [error-classification.md](./error-classification.md) for category definitions.

## Transient Error Handling

**Strategy:** Retry with exponential backoff.

| Parameter | Value |
|-----------|-------|
| Base delay | 1 second |
| Max delay | 60 seconds |
| Max attempts | 5 |
| Jitter | 0-500ms random |

```python
def retry_transient(attempt):
    delay = min(60, (2 ** attempt) + random.uniform(0, 0.5))
    sleep(delay)
    return attempt < 5
```

**Escalation Path:**
1. After 5 retries: log as persistent transient
2. Route to DETOUR if alternative path exists (e.g., different API endpoint)
3. After DETOUR fails: ESCALATE to human

**Logging:**
```json
{
  "error_category": "transient",
  "error_type": "rate_limit",
  "attempt": 3,
  "delay_ms": 4000,
  "will_retry": true,
  "context": {
    "endpoint": "api.anthropic.com",
    "http_status": 429,
    "retry_after": "5s"
  }
}
```

See [retry-policy.md](./retry-policy.md) for complete retry configuration.

## Permanent Error Handling

**Strategy:** Fail fast, capture context, route to recovery.

```python
def handle_permanent(error):
    log_with_context(error, level="ERROR")
    if is_missing_input(error):
        return RoutingDecision(status="BLOCKED", reason=str(error))
    elif is_config_error(error):
        return RoutingDecision(decision="ESCALATE", reason="Configuration issue")
    else:
        return RoutingDecision(status="UNVERIFIED", concerns=[error_to_concern(error)])
```

**Escalation Path:**
1. Log full error with context
2. If missing input: BLOCKED
3. If fixable by agent: DETOUR to fixer
4. If human decision needed: ESCALATE immediately

**Logging:**
```json
{
  "error_category": "permanent",
  "error_type": "validation_error",
  "will_retry": false,
  "routing_decision": "BLOCKED",
  "context": {
    "field": "api_key",
    "error": "Invalid format: expected sk-... pattern",
    "input_source": "config/secrets.yaml"
  },
  "stack_trace": "..."
}
```

## Retriable Error Handling

**Strategy:** Limited retries with signature tracking.

| Parameter | Value |
|-----------|-------|
| Max attempts | 3 |
| Backoff | None (failures are random) |
| Signature tracking | Required |

```python
def retry_retriable(attempt, failure_signature, history):
    if attempt >= 3:
        return False  # Stop retrying
    if signature_in_history(failure_signature, history, count=2):
        return False  # Same error twice = not flaky
    return True
```

**Escalation Path:**
1. Retry up to 3 times
2. If same signature twice: route to DETOUR (known fix pattern)
3. If DETOUR fails: advance with WARNING
4. If critical path: ESCALATE

**Logging:**
```json
{
  "error_category": "retriable",
  "error_type": "flaky_test",
  "attempt": 2,
  "will_retry": true,
  "failure_signature": "test_auth_login::assertion_failed",
  "previous_signatures": ["test_db_connect::timeout"],
  "context": {
    "test_file": "tests/test_auth.py",
    "test_name": "test_login",
    "failure_message": "Expected 200, got 503"
  }
}
```

## Fatal Error Handling

**Strategy:** Halt immediately, preserve state, alert human.

```python
def handle_fatal(error):
    # Stop everything
    halt_all_agents()

    # Preserve evidence
    snapshot_state_to_forensics()

    # Alert
    notify_operator(error, priority="CRITICAL")

    # Log with full context
    log_fatal_error(error)

    # Return terminal state
    return RoutingDecision(
        decision="TERMINATE",
        reason=f"FATAL: {error.type}",
        requires_human=True
    )
```

**Escalation Path:** None. Fatal errors terminate the run immediately.

**Logging:**
```json
{
  "error_category": "fatal",
  "error_type": "secrets_exposure",
  "halted_at": "build-step-5",
  "action_taken": "TERMINATE",
  "context": {
    "secret_type": "api_key",
    "location": "src/config.py:15",
    "exposure_risk": "Would be committed to git"
  },
  "forensics": {
    "state_snapshot": "RUN_BASE/build/forensics/fatal-001/",
    "artifacts_preserved": ["diff.patch", "receipt.json", "env_dump.json"]
  },
  "notification_sent": true
}
```

## Routing Integration

Errors map to routing decisions:

| Error Category | Routing Decision | Condition |
|----------------|------------------|-----------|
| Transient | (internal retry) | attempts < max |
| Transient | DETOUR | alternative path exists |
| Transient | ESCALATE | retries exhausted |
| Permanent | BLOCKED | missing input |
| Permanent | DETOUR | fixable by agent |
| Permanent | ESCALATE | human decision needed |
| Retriable | (internal retry) | attempts < 3 |
| Retriable | DETOUR | signature matches known fix |
| Retriable | CONTINUE | advance with warning |
| Fatal | TERMINATE | always |

## The Rule

> Transient: retry with backoff. Permanent: fail fast.
> Retriable: try again with limits. Fatal: halt immediately.
> When in doubt, advance with documented concerns.

---

## See Also
- [error-classification.md](./error-classification.md) - Category definitions
- [error-aggregation.md](./error-aggregation.md) - Multiple error resolution
- [timeout-policy.md](./timeout-policy.md) - Timeout configuration
- [retry-policy.md](./retry-policy.md) - Retry strategies
- [circuit-breaker.md](./circuit-breaker.md) - Cascade prevention
- [detour-catalog.md](./detour-catalog.md) - Known fix patterns
- [resume-protocol.md](./resume-protocol.md) - Recovery from failures
