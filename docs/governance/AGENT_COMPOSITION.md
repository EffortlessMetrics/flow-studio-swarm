# Agent Composition

Use composition only when work requires it.

## Four Patterns

| Pattern | Use When |
|---------|----------|
| Sequential Chain | Pipelines (A → B → C) |
| Adversarial Loop | Quality improvement (author ↔ critic) |
| Fan-Out/Fan-In | Parallel independent work |
| Specialist Delegation | Deep dive on subproblem |

## Spawn Test

Spawn an agent for exactly two reasons:
1. **Work**: Something needs changing
2. **Compression**: Context needs compressing

If neither applies, don't spawn.

## Anti-Patterns

- Coordinator that only routes (that's orchestrator's job)
- Validator that checks boolean (that's a skill, no LLM)
- Approver that rubber-stamps (if can't reject, don't spawn)
- Agent per file (over-decomposition)
- Self-reviewing agent (no adversarial tension)

## Rules

- Every spawn must produce work or compression
- 3 agents with 2k overhead each = 6k wasted
- If task fits in one context, don't shard
