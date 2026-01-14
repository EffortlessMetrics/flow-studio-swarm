# Observability Contract

Logs are the runtime audit trail. They capture what happened, when, and why.

## Overview

The observability contract is split into three focused documents:

| Document | Purpose |
|----------|---------|
| [observability-schema.md](./observability-schema.md) | Log format, required/optional fields, log levels |
| [observability-content.md](./observability-content.md) | What to always log, what to never log |
| [observability-placement.md](./observability-placement.md) | Trace correlation, log locations, rotation |

## The Rule

> Logs are structured, correlated, and safe.
> Required fields enable querying. Forbidden content prevents leaks.
> `run_id` ties everything together. Step logs are the primary unit.

## Quick Reference

### Required Fields
- `timestamp`, `level`, `run_id`, `flow_key`, `step_id`, `agent_key`, `message`

### Log Levels
- **ERROR**: Failures needing attention
- **WARN**: Concerns that don't block
- **INFO**: Step transitions, key decisions
- **DEBUG**: Detailed execution (off by default)

### Never Log
- Secrets (API keys, passwords, tokens)
- Full file contents
- PII (emails, names, addresses)
- Raw LLM responses

## Validation

Log validation checks:
1. Required fields present
2. Timestamps are valid ISO8601
3. Level is valid enum
4. No forbidden patterns (secrets, PII)
5. Paths resolve (when claimed)

## Anti-Patterns

### Unstructured Logs
```
// BAD
console.log("Step 3 completed successfully!")

// GOOD
logger.info({ event: "step_end", step_id: "step-3", status: "succeeded" })
```

### Missing Correlation
```json
// BAD - no run_id or step_id
{ "message": "Something happened" }

// GOOD - fully correlated
{ "run_id": "abc123", "step_id": "step-3", "message": "Something happened" }
```

### Secret Leakage
```json
// BAD
{ "api_key": "sk-abc123..." }

// GOOD
{ "api_key_present": true }
```

### Content Dumping
```json
// BAD
{ "file": { "path": "src/auth.py", "content": "..." } }

// GOOD
{ "artifact_path": "src/auth.py", "size_bytes": 1234 }
```

---

## See Also
- [observability-schema.md](./observability-schema.md) - Log format and fields
- [observability-content.md](./observability-content.md) - What to log and what to never log
- [observability-placement.md](./observability-placement.md) - Correlation and location
- [receipt-schema.md](./receipt-schema.md) - Step-level proof of work
- [handoff-protocol.md](./handoff-protocol.md) - Step transition protocol
- [off-road-logging.md](./off-road-logging.md) - Routing decision audit trail
