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

Verbose handoffs = design bloat signal.

> Docs: docs/execution/TOKEN_BUDGETS.md
