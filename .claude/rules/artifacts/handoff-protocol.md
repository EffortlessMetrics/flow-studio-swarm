# Handoff Protocol

Handoffs transfer state between steps.

## Envelope Structure
```json
{
  "meta": {"step_id", "flow_key", "agent_key", "timestamp"},
  "status": "VERIFIED | UNVERIFIED | BLOCKED",
  "summary": {"what_i_did", "what_i_found", "evidence": {"artifacts_produced", "commands_run"}},
  "concerns": [{"severity", "description", "location", "recommendation"}],
  "assumptions": [{"assumption", "why", "impact_if_wrong"}],
  "routing": {"recommendation", "can_further_iteration_help", "reason"}
}
```

## Status Meanings
- VERIFIED: Complete, requirements met → advance
- UNVERIFIED: Complete, concerns documented → critic decides
- BLOCKED: Cannot proceed → human intervention (rare)

## Placement
`RUN_BASE/<flow>/handoffs/<step_id>-<agent_key>.json`

> Docs: docs/artifacts/HANDOFF_PROTOCOL.md
