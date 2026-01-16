# Minimal Handoffs

Critic → Author in microloops. Target: <500 tokens.

## The Rule
Focus on ONE issue with file:line and actionable recommendation.

## Good
```json
{
  "status": "UNVERIFIED",
  "concerns": [{"severity": "HIGH", "description": "Missing validation", "location": "src/auth.py:42"}],
  "routing": {"recommendation": "LOOP", "can_further_iteration_help": true}
}
```

Verbose prose wastes tokens. Missing line numbers waste author time.

> Docs: docs/execution/HANDOFF_PROTOCOL.md
