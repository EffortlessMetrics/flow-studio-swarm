# Data Retention

Artifacts have finite lifetimes.

## Default Periods

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

## Privacy

- Never retain secrets in logs/receipts
- Redact before archival if needed
- Treat any accidental capture as incident
