# Context Budgets

Work gets 80%. Coordination gets 20%. Intelligence degrades as irrelevant history grows.

## Session Amnesia

Each step starts fresh. Rehydrate from:
- Artifacts on disk (primary)
- Handoff envelopes (structured)
- Scent trail (decisions)

NOT from: conversation history, previous reasoning, abandoned approaches.

## Loading Priority

| Priority | Content | Drop Policy |
|----------|---------|-------------|
| CRITICAL | Teaching notes, step spec | Never drop |
| HIGH | Previous step output | Truncate if needed |
| MEDIUM | Referenced artifacts | On-demand |
| LOW | History summary | Drop first |

## The Rule

- When over budget: drop LOW first, truncate MEDIUM, never drop CRITICAL
- Heavy loaders compress: one reads 50k, produces 2k, ten downstream save 480k
- Summarize before loading (> 10k = always summarize)
- Paths over contents. Structured over prose.
- Kitchen sink loading = design problem

> Docs: docs/execution/CONTEXT_BUDGETS.md
