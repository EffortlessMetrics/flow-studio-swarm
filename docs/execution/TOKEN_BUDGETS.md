# Token Budgets

Work gets 80%. Coordination gets 20%.

## By Role

| Role | Budget | Rationale |
|------|--------|-----------|
| Implementer | Higher | Needs codebase context |
| Critic | Lower | Focused review |
| Navigator | Minimal | Compact forensics only |

## Overflow Handling

1. Drop LOW priority first
2. Truncate MEDIUM
3. Never drop CRITICAL (teaching notes)

## Compression Patterns

| Instead of | Use |
|------------|-----|
| Inline content | Path reference |
| Full file | Diff or excerpt |
| Prose explanation | Structured JSON |
| Test output | Summary + evidence path |

## Anti-Patterns

- Kitchen Sink: load everything "just in case"
- Narrator: verbose explanations
- Repeater: re-stating instructions
- Copy-Paster: full output inline

Verbose handoffs = design bloat signal.

See also: [../CONTEXT_BUDGETS.md](../CONTEXT_BUDGETS.md)
