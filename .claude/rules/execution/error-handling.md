# Error Handling

Each error category has a specific handling strategy.

## Strategies by Category
| Category | Strategy | Max Retries |
|----------|----------|-------------|
| **Transient** | Retry with exponential backoff | 5 |
| **Permanent** | Fail fast, capture context | 0 |
| **Retriable** | Limited retries, no backoff | 3 |
| **Fatal** | Halt immediately, preserve state | 0 |

## Routing
- Transient exhausted → DETOUR or ESCALATE
- Permanent → BLOCKED or ESCALATE
- Retriable with same signature 2x → DETOUR to known fix
- Fatal → TERMINATE

## The Rule
- Transient: retry with backoff
- Permanent: fail fast
- Retriable: try again with limits
- Fatal: halt immediately
- When in doubt, advance with documented concerns

> Skill: error-triage
> Docs: docs/execution/ERROR_TAXONOMY.md
