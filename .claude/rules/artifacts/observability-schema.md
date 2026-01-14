# Observability Schema: Structured Logging

All logs use JSON Lines (JSONL) format. One JSON object per line.

## Required Fields

Every log entry MUST include:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO | WARN | ERROR | DEBUG",
  "run_id": "abc123",
  "flow_key": "signal | plan | build | review | gate | deploy | wisdom",
  "step_id": "step-3",
  "agent_key": "code-implementer",
  "message": "Human-readable description"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO8601 | When the event occurred |
| `level` | enum | Severity level |
| `run_id` | string | Unique run identifier |
| `flow_key` | enum | Current flow |
| `step_id` | string | Current step |
| `agent_key` | string | Active agent |
| `message` | string | Human-readable description |

## Optional Fields

```json
{
  "tokens": {
    "prompt": 1500,
    "completion": 500,
    "total": 2000
  },
  "duration_ms": 1234,
  "error": {
    "type": "ValidationError",
    "message": "Missing required field: step_id",
    "stack": "string (DEBUG only)"
  },
  "parent_step_id": "step-2",
  "child_step_id": "substep-3a",
  "routing": {
    "decision": "CONTINUE | LOOP | DETOUR | ...",
    "reason": "string"
  },
  "artifact_path": "RUN_BASE/build/output.json",
  "command": "pytest tests/ -v",
  "exit_code": 0,
  "event": "step_start | step_end | routing_decision | ..."
}
```

### Token Fields

| Field | Type | Description |
|-------|------|-------------|
| `tokens.prompt` | number | Input tokens |
| `tokens.completion` | number | Output tokens |
| `tokens.total` | number | Total tokens |
| `tokens.used` | number | Used (for budget warnings) |
| `tokens.budget` | number | Allocated budget |
| `tokens.remaining` | number | Remaining budget |

### Error Fields

| Field | Type | Description |
|-------|------|-------------|
| `error.type` | string | Error class name |
| `error.message` | string | Error description |
| `error.stack` | string | Stack trace (DEBUG only) |
| `error.command` | string | Failed command (if applicable) |
| `error.exit_code` | number | Exit code (if applicable) |
| `error.evidence_path` | string | Path to error output |

## Log Levels

| Level | Purpose | When to Use |
|-------|---------|-------------|
| **ERROR** | Failures that need attention | Step failed, unhandled exception, missing required input |
| **WARN** | Concerns that don't block | Assumption made, evidence gap, retry attempted |
| **INFO** | Step transitions, key decisions | Step start/end, routing decision, artifact produced |
| **DEBUG** | Detailed execution | Tool calls, context loading, internal state (off by default) |

### Level Selection Guide

```
ERROR: "Step failed: pytest returned exit code 1"
WARN:  "Assumption: user means OAuth when they say 'login'"
INFO:  "Step build-step-3 completed in 4523ms"
DEBUG: "Loading context: 15234 tokens from previous step"
```

### Level Selection Rules

| Situation | Level | Rationale |
|-----------|-------|-----------|
| Step cannot complete | ERROR | Needs attention |
| Assumption made | WARN | Document but don't block |
| Normal progression | INFO | Audit trail |
| Internal mechanics | DEBUG | Troubleshooting only |

## Event Types

Common `event` field values:

| Event | Description | Required Fields |
|-------|-------------|-----------------|
| `step_start` | Step begins execution | `step_id`, `agent_key` |
| `step_end` | Step completes | `duration_ms`, `status`, `tokens` |
| `step_error` | Step fails | `error` object |
| `routing_decision` | Navigator decides | `routing` object |
| `subagent_spawn` | Subagent created | `child_step_id` |
| `token_warning` | Budget threshold | `tokens.used`, `tokens.budget` |

## The Rule

> All logs are JSONL. Required fields enable querying.
> Levels indicate severity. Events categorize entries.

---

## See Also
- [observability-content.md](./observability-content.md) - What to log and what to never log
- [observability-placement.md](./observability-placement.md) - Where logs go and how to correlate
- [observability-contract.md](./observability-contract.md) - Overview and validation
