# Data Retention

Artifacts have finite lifetimes.

## Periods
| Type | Retention |
|------|-----------|
| Run artifacts | 30 days |
| Receipts | 90 days |
| LLM transcripts | 7 days (privacy) |
| Git history | Forever |

## Exceptions
- Open PRs: retain until PR closes
- Incidents: retain until post-mortem complete
- Compliance holds: never delete

## The Rule
Automate cleanup. Honor exceptions. Never delete git history.

> Docs: docs/artifacts/DATA_RETENTION.md
