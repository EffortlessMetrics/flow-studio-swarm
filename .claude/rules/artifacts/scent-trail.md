# Scent Trail

How does an agent know "how we got here"? Scent trail provides breadcrumbs.

## Purpose
Compact summary of:
- Key decisions made
- Why they were made
- What alternatives were rejected
- What assumptions are in effect

## Schema
```json
{
  "scent_trail": {
    "flow_objective": "string",
    "decisions": [
      { "step": "...", "decision": "...", "rationale": "...", "confidence": "HIGH|MEDIUM|LOW" }
    ],
    "assumptions_in_effect": [
      { "assumption": "...", "made_at": "...", "impact_if_wrong": "..." }
    ],
    "open_questions": ["..."]
  }
}
```

## When to Update
Add decision when: architectural choice, technology choice, approach selection, assumption adoption.
Don't add: variable naming, formatting, trivial choices.

## The Rule
- Every step receives and updates the scent trail
- Prior decisions are respected unless explicitly revisited
- Conflicts are flagged, not silently overridden

> Docs: docs/artifacts/SCENT_TRAIL.md
