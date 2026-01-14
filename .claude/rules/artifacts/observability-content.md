# Observability Content: What to Log

This rule defines what MUST be logged and what MUST NEVER be logged.

## What to Always Log

### Step Lifecycle

Every step logs start and end:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "run_id": "abc123",
  "flow_key": "build",
  "step_id": "step-3",
  "agent_key": "code-implementer",
  "message": "Step started",
  "event": "step_start"
}
```

```json
{
  "timestamp": "2024-01-15T10:30:04.523Z",
  "level": "INFO",
  "run_id": "abc123",
  "flow_key": "build",
  "step_id": "step-3",
  "agent_key": "code-implementer",
  "message": "Step completed",
  "event": "step_end",
  "duration_ms": 4523,
  "status": "succeeded",
  "tokens": {
    "prompt": 15000,
    "completion": 3500,
    "total": 18500
  }
}
```

### Routing Decisions

```json
{
  "timestamp": "2024-01-15T10:30:04.600Z",
  "level": "INFO",
  "run_id": "abc123",
  "flow_key": "build",
  "step_id": "step-3",
  "agent_key": "navigator",
  "message": "Routing decision: CONTINUE to step-4",
  "event": "routing_decision",
  "routing": {
    "decision": "CONTINUE",
    "next_step_id": "step-4",
    "reason": "Tests passed, no HIGH severity concerns"
  }
}
```

### Error Details

```json
{
  "timestamp": "2024-01-15T10:30:04.523Z",
  "level": "ERROR",
  "run_id": "abc123",
  "flow_key": "build",
  "step_id": "step-3",
  "agent_key": "code-implementer",
  "message": "Step failed: pytest returned exit code 1",
  "event": "step_error",
  "error": {
    "type": "CommandError",
    "message": "pytest returned exit code 1",
    "command": "pytest tests/ -v",
    "exit_code": 1,
    "evidence_path": "RUN_BASE/build/test_output.log"
  }
}
```

### Token Usage

Always in `step_end`. Also log when approaching limits:

```json
{
  "timestamp": "2024-01-15T10:30:03.000Z",
  "level": "WARN",
  "run_id": "abc123",
  "flow_key": "build",
  "step_id": "step-3",
  "agent_key": "code-implementer",
  "message": "Token budget 90% consumed",
  "event": "token_warning",
  "tokens": {
    "used": 27000,
    "budget": 30000,
    "remaining": 3000
  }
}
```

## What to Never Log

### Secrets and Credentials

NEVER log:
- API keys (`sk-...`, `ghp_...`, `AKIA...`)
- Passwords or tokens
- Private keys
- Connection strings with credentials
- Bearer tokens

**Enforcement:** Redact patterns matching known secret formats.

### Full File Contents

NEVER log file contents. Log paths instead:

```json
// BAD
{ "file_content": "def auth():\n    password = 'secret123'\n..." }

// GOOD
{ "artifact_path": "src/auth.py", "lines_modified": 45 }
```

### PII

NEVER log:
- Email addresses
- Names
- Phone numbers
- Addresses
- Any user-identifiable information

### Raw LLM Responses

NEVER log raw LLM output in structured logs. Write to transcript file instead:

```json
// BAD
{ "llm_response": "Here is the implementation:\n\n```python\n..." }

// GOOD
{ "transcript_path": "RUN_BASE/build/llm/step-3-code-implementer.jsonl" }
```

## Content Summary

| Always Log | Never Log |
|------------|-----------|
| Step start/end | Secrets |
| Routing decisions | Full file contents |
| Error details | PII |
| Token usage | Raw LLM responses |
| Artifact paths | Connection strings |
| Exit codes | Bearer tokens |
| Durations | Private keys |

## The Rule

> Log events, not content. Log paths, not files.
> Secrets and PII are never logged. Redact before write.

---

## See Also
- [observability-schema.md](./observability-schema.md) - Log format and fields
- [observability-placement.md](./observability-placement.md) - Where logs go and correlation
- [secret-management.md](../safety/secret-management.md) - Secret handling
