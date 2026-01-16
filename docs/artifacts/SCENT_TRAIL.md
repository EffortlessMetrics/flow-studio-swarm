# Scent Trail

Scent trail records decisions so downstream steps don't re-explain.

## Schema

```json
{
  "flow_objective": "...",
  "decisions": [{"step", "decision", "rationale", "confidence"}],
  "assumptions_in_effect": [{"assumption", "made_at", "impact_if_wrong"}],
  "open_questions": ["..."]
}
```

## Rules

- Prior decisions are respected unless explicitly revisited
- Referenced in handoffs; never re-narrated
- Reduces context bloat

See also: [explanation/SCENT_TRAIL.md](../explanation/SCENT_TRAIL.md)
