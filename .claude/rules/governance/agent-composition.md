# Agent Composition

Spawn for exactly two reasons: **Work** or **Compression**.

## When to Spawn

**Single agent**: Task is focused, no conflicting roles, context fits in budget
**Multiple agents**: Adversarial tension needed, different expertise, context would exceed budget, parallel work possible

## Patterns

| Pattern | Use When |
|---------|----------|
| Sequential Chain | Pipelines (A → B → C) |
| Adversarial Loop | Quality improvement (author ↔ critic) |
| Fan-Out/Fan-In | Parallel independent work |
| Specialist Delegation | Deep dive on subproblem |

## Anti-Patterns

- Coordinator that only routes (orchestrator's job)
- Validator that checks boolean (skill, no LLM)
- Approver that rubber-stamps (if can't reject, don't spawn)
- Self-reviewing agent (no adversarial tension)

## The Rule

- Every spawn must produce work or compression
- If task fits in one context, don't shard
- 3 agents with 2k overhead each = 6k wasted

> Docs: docs/governance/AGENT_COMPOSITION.md
