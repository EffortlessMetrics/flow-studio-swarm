# Handoff Protocol

Handoffs transfer state between steps.

## Envelope Structure

```json
{
  "meta": {"step_id", "flow_key", "agent_key", "timestamp"},
  "status": "VERIFIED | UNVERIFIED | BLOCKED",
  "summary": {"what_i_did", "what_i_found", "evidence"},
  "concerns": [{"severity", "description", "location"}],
  "assumptions": [{"assumption", "why", "impact_if_wrong"}],
  "routing": {"recommendation", "can_further_iteration_help", "reason"}
}
```

## Sizing

| Type | Size | Use |
|------|------|-----|
| Minimal | <500 tokens | Microloop iterations |
| Standard | 500-2000 | Sequential steps |
| Heavy | 2000-5000 | Flow boundaries |

## Rules

- Pointers over content
- Structure over prose
- Never transcribe full outputs
