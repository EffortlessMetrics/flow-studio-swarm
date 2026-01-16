# Token Waste Patterns

Tokens are cheap but not free. Waste indicates design problems.

## Anti-Patterns
| Pattern | Problem | Fix |
|---------|---------|-----|
| **Kitchen Sink** | Load everything "just in case" | Load only what teaching notes require |
| **Narrator** | Verbose explanations | Structured output schemas |
| **Repeater** | Re-stating instructions | Trust kernel loads once |
| **Copy-Paster** | Full output inline | Write to file, include pointer |

## Design Signals
| Signal | Problem | Fix |
|--------|---------|-----|
| Steps > budget | Scope too broad | Split into smaller steps |
| High coordination % | Too many steps | Consolidate |
| Repeated content | Context discipline failing | Enforce loading hierarchy |
| Verbose outputs | Missing schemas | Add output schema |

## The Rule
- Every token should earn its place
- Bloated context = model drift, reduced quality, budget overruns
- Load conversation history = wrong (rehydrate from artifacts)

> Docs: docs/execution/TOKEN_BUDGETS.md
