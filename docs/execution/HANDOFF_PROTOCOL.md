# Handoff Protocol (Execution)

Handoffs are pointers + decisions. Never inline large content.

## Minimal Handoffs (<500 tokens)

For critic → author microloops. Focus on ONE issue with file:line.

```json
{
  "status": "UNVERIFIED",
  "concerns": [{"severity": "HIGH", "description": "...", "location": "src/auth.py:42"}],
  "routing": {"recommendation": "LOOP", "can_further_iteration_help": true}
}
```

## Standard Handoffs (500-2000)

Step-to-step. Includes: meta, summary, assumptions, routing.

## Heavy Handoffs (2000-5000)

Flow boundaries. Standard plus: plan_summary, dependencies, test_strategy.

## Rules

- Verbose prose wastes tokens
- Missing line numbers waste author time
- Use scent trail for prior decisions

See also: [../artifacts/HANDOFF_PROTOCOL.md](../artifacts/HANDOFF_PROTOCOL.md)
