# Scent Trail

How agents know "how we got here."

## Schema
```json
{
  "flow_objective": "...",
  "decisions": [{"step", "decision", "rationale", "confidence"}],
  "assumptions_in_effect": [{"assumption", "made_at", "impact_if_wrong"}],
  "open_questions": ["..."]
}
```

## The Rule
Prior decisions are respected unless explicitly revisited.

> Docs: docs/artifacts/SCENT_TRAIL.md
