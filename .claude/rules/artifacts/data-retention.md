# Data Retention

Artifacts have finite lifetimes.

## Periods

| Type | Retention |
|------|-----------|
| Run artifacts | 30 days |
| Receipts | 90 days |
| LLM transcripts | 7 days (no archival, delete) |
| Git history | Forever |

## Exception Priority

Compliance > Incident > Open PR > Standard

## The Rule

- Automate cleanup. Honor exceptions. Never delete git history.
- LLM transcripts may contain PII: delete, don't archive
- Past retention + no exception → delete
- Exception applies → retain until condition clears

> Docs: docs/artifacts/DATA_RETENTION.md
