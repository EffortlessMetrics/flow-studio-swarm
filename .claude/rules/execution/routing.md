# Routing

Graph-native routing with goal-aligned decisions.

## Vocabulary (Closed Set)

| Decision | When |
|----------|------|
| CONTINUE | Normal progression |
| LOOP | Microloop iteration |
| DETOUR | Known failure pattern |
| INJECT_FLOW | Insert entire flow (e.g., Flow 8 rebase) |
| ESCALATE | Need human decision |
| TERMINATE | Flow complete |

## Priority Order

1. Fast-path (deterministic, no LLM) → route directly
2. Navigator (LLM, bounded forensics) → route with judgment
3. Escalate → failure case

## Navigator Contract

Input: compact forensics (step, agent, status, tests, lint, diff, iteration count)
Output: bounded decision from vocabulary above
Model: economy tier (haiku) for speed

## The Rule

- Every decision: "Does this help achieve the flow's objective?"
- Routes based on forensics, not narrative
- When in doubt, escalate—never guess

> Docs: docs/execution/ROUTING_PROTOCOL.md
