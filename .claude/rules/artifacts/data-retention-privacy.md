# Data Retention Privacy

LLM transcripts and logs may contain PII. This rule defines privacy handling for retained data.

## PII in Logs/Transcripts

LLM transcripts may contain:
- User input with PII
- Generated content with PII
- Error messages with paths/usernames

**Mitigations:**
- 7-day transcript retention (shortest period)
- No transcript archival (delete, don't archive)
- Redaction before archival if needed

## Right to Deletion Requests

On deletion request:

1. Identify all runs containing requester's data
2. Apply compliance hold (preserve for audit)
3. Delete identified artifacts
4. Document deletion in audit log
5. Release hold after confirmation

### Deletion Request Schema

```yaml
deletion_request:
  requester: "user@example.com"
  received: "2024-01-15"
  runs_identified: ["run-001", "run-002"]
  status: "pending | in_progress | completed"
  completed: "2024-01-16"
  audit_log: "deletions/2024-01-16-user.log"
```

### Response Timeline

| Severity | Response Time |
|----------|---------------|
| Standard request | 30 days |
| Urgent (legal) | 7 days |
| Security incident | Immediate |

## Anonymization Options

For runs needed beyond transcript retention:

```python
def anonymize_transcript(transcript_path):
    """Remove PII while preserving structure."""
    # Replace emails with placeholders
    # Replace usernames with generic identifiers
    # Replace file paths with sanitized versions
    # Keep token counts and timestamps
```

Anonymized transcripts can be retained longer for analysis.

### What to Anonymize

| PII Type | Replacement |
|----------|-------------|
| Email addresses | `[EMAIL_REDACTED]` |
| Usernames | `[USER_001]`, `[USER_002]` |
| File paths with usernames | `/home/[USER]/...` |
| IP addresses | `[IP_REDACTED]` |
| Phone numbers | `[PHONE_REDACTED]` |

### What to Preserve

Keep these for analysis value:
- Token counts
- Timestamps
- Step/flow identifiers
- Agent keys
- Status values
- Error types (not messages)

## The Rule

> Transcripts contain PII. Treat accordingly.
> Delete before archive for transcripts.
> Honor deletion requests with audit trail.

---

## See Also
- [data-retention.md](./data-retention.md) - Overview and commands
- [data-retention-lifecycle.md](./data-retention-lifecycle.md) - Retention periods
- [data-retention-exceptions.md](./data-retention-exceptions.md) - Exception handling
- [../safety/secret-management.md](../safety/secret-management.md) - Secret handling
