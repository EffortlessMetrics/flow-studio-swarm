# Error Aggregation

When multiple errors occur simultaneously, which wins? This document defines precedence and aggregation rules.

## Precedence Order

Higher categories override lower ones:

```
1. FATAL     → Always wins. Halt immediately.
2. PERMANENT → Cannot proceed. Block or escalate.
3. RETRIABLE → Try again with limits.
4. TRANSIENT → Retry with backoff.
```

## Aggregation Logic

```python
def aggregate_errors(errors):
    # Fatal always wins
    if any(e.category == "fatal" for e in errors):
        return max(errors, key=lambda e: e.severity, default=None)

    # Permanent over retriable over transient
    by_category = {
        "permanent": [],
        "retriable": [],
        "transient": []
    }
    for e in errors:
        by_category[e.category].append(e)

    if by_category["permanent"]:
        return aggregate_permanent(by_category["permanent"])

    if by_category["retriable"]:
        return aggregate_retriable(by_category["retriable"])

    return aggregate_transient(by_category["transient"])
```

## Same-Category Aggregation

| Category | Aggregation Rule |
|----------|------------------|
| Fatal | First fatal wins (stop immediately) |
| Permanent | Collect all, report together, use highest severity |
| Retriable | Track signatures, retry if any might succeed |
| Transient | Use longest backoff, retry once |

## Example: Mixed Errors

When errors from multiple categories occur together:

```json
{
  "errors": [
    { "category": "transient", "type": "rate_limit" },
    { "category": "permanent", "type": "validation_error" },
    { "category": "retriable", "type": "flaky_test" }
  ],
  "aggregation": {
    "winning_category": "permanent",
    "decision": "BLOCKED",
    "reason": "Validation error cannot be retried",
    "suppressed": [
      { "category": "transient", "note": "Would retry, but permanent blocks" },
      { "category": "retriable", "note": "Would retry, but permanent blocks" }
    ]
  }
}
```

## Required Context (All Errors)

Every aggregated error result must capture:

```json
{
  "timestamp": "ISO8601",
  "run_id": "string",
  "flow_key": "string",
  "step_id": "string",
  "agent_key": "string",
  "error_category": "transient | permanent | retriable | fatal",
  "error_type": "string (specific type)",
  "error_message": "string",
  "stack_trace": "string (if available)"
}
```

## Category-Specific Context

### Transient
```json
{
  "retry_count": 3,
  "total_delay_ms": 7000,
  "endpoint": "api.anthropic.com",
  "http_status": 429,
  "retry_after_header": "5"
}
```

### Permanent
```json
{
  "input_source": "path or identifier",
  "validation_errors": [],
  "expected_format": "description",
  "actual_value": "sanitized value"
}
```

### Retriable
```json
{
  "failure_signature": "hash or pattern",
  "previous_signatures": [],
  "test_output": "truncated output",
  "flaky_history": []
}
```

### Fatal
```json
{
  "halt_reason": "string",
  "affected_resources": [],
  "remediation_steps": [],
  "forensics_path": "RUN_BASE/.../forensics/",
  "notification_id": "string"
}
```

## The Rule

> Fatal wins. Permanent blocks. Retriable yields. Transient waits.
> When aggregating, the highest category determines the outcome.
> Lower-category errors are suppressed but logged.

---

## See Also
- [error-classification.md](./error-classification.md) - Category definitions
- [error-handling.md](./error-handling.md) - Handling strategies
- [routing-decisions.md](./routing-decisions.md) - Decision vocabulary
