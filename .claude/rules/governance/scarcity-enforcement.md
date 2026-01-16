# Scarcity Enforcement

Scarcity is a feature, not a bug. Budgets enforce discipline.

## Context Loading Priority

| Priority | Content | Drop Policy |
|----------|---------|-------------|
| CRITICAL | Teaching notes, step spec | Never drop |
| HIGH | Previous step output | Truncate if needed |
| MEDIUM | Referenced artifacts | On-demand |
| LOW | History summary | Drop first |

## Session Amnesia

Each step starts fresh. Rehydrate from:
- Artifacts on disk (primary)
- Handoff envelopes (structured)
- Scent trail (decisions)

NOT from: conversation history, previous reasoning, abandoned approaches.

## The Rule

> When over budget: drop LOW first, truncate MEDIUM, never drop CRITICAL.

> Docs: docs/explanation/SCARCITY_AS_DESIGN.md
