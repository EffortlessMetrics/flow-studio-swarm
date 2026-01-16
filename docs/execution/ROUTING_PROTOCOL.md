# Routing Protocol (Execution)

Graph-native routing with goal-aligned decisions.

## Decision Vocabulary

| Decision | When |
|----------|------|
| CONTINUE | Normal progression |
| LOOP | Microloop iteration |
| DETOUR | Known failure pattern |
| INJECT_FLOW | Insert entire flow (e.g., Flow 8 rebase) |
| ESCALATE | Need human decision |
| TERMINATE | Flow complete |

## Priority Order

1. Fast-path (deterministic, no LLM)
2. Navigator (LLM, bounded forensics)
3. Escalate (failure case)

## Navigator Protocol

Navigator routes based on forensics, not narrative.
- Input: compact forensics (tests, lint, diff, concerns)
- Output: bounded decision from closed vocabulary
- Uses economy tier (haiku) for speed

See also: [../ROUTING_PROTOCOL.md](../ROUTING_PROTOCOL.md), [../explanation/NAVIGATOR_PROTOCOL.md](../explanation/NAVIGATOR_PROTOCOL.md)
