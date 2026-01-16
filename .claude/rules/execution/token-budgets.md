# Token Budgets

Work gets 80%. Coordination gets 20%.

## Overflow Handling

1. Drop LOW priority first
2. Truncate MEDIUM
3. Never drop CRITICAL (teaching notes)

## The Rule

- Heavy loaders compress: one reads 50k, produces 2k, ten downstream save 480k
- Summarize before loading (> 10k = always summarize)
- Use paths, not contents. Structured over prose.
- Rehydrate from artifacts, not conversation history
- Kitchen sink loading, verbose explanations, inline content = design problems

> Docs: docs/execution/TOKEN_BUDGETS.md
