# Routing Decisions

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

## Priority
1. Fast-path (deterministic, no LLM)
2. Navigator (LLM, bounded forensics)
3. Escalate (failure case)

Every decision: "Does this help achieve the flow's objective?"

> Docs: docs/execution/ROUTING_PROTOCOL.md
