# Observability

Logs are structured, correlated, and safe.

## Event Schema (JSONL)

```json
{"timestamp": "ISO8601", "level": "INFO|WARN|ERROR|DEBUG",
 "run_id": "...", "flow_key": "...", "step_id": "...",
 "agent_key": "...", "message": "..."}
```

## Placement

| Scope | Path |
|-------|------|
| Step | `RUN_BASE/<flow>/logs/<step_id>.jsonl` |
| Flow | `RUN_BASE/<flow>/logs/flow.jsonl` |
| Run | `RUN_BASE/logs/run.jsonl` |

## Content Rules

- Log events, not content
- Log paths, not files
- Never log secrets or PII

See also: [explanation/OBSERVABLE_BY_DEFAULT.md](../explanation/OBSERVABLE_BY_DEFAULT.md)
