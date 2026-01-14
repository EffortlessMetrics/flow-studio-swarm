# Data Retention Lifecycle

Artifacts have finite lifetimes. This rule defines retention periods and cleanup policies.

## Why Retention Matters

Without retention policies:
- Storage grows unbounded
- Old artifacts become noise
- Privacy obligations go unmet
- Costs accumulate silently

With retention policies:
- Predictable storage costs
- Relevant data stays accessible
- Compliance requirements met
- Cleanup is automated

## Retention Periods

| Artifact Type | Location | Retention | Rationale |
|---------------|----------|-----------|-----------|
| Run artifacts | `RUN_BASE/<run-id>/` | 30 days | Debugging window |
| Receipts | `RUN_BASE/<flow>/receipts/` | 90 days | Audit trail |
| LLM transcripts | `RUN_BASE/<flow>/llm/` | 7 days | Cost, privacy |
| Logs | `RUN_BASE/<flow>/logs/` | 30 days | Debugging |
| Handoff envelopes | `RUN_BASE/<flow>/handoffs/` | 30 days | Debugging |
| Routing decisions | `RUN_BASE/<flow>/routing/` | 90 days | Audit trail |
| Git history | `.git/` | Forever | Source of truth |

## Cleanup Policies

### Automated Cleanup Job

Run daily at low-traffic hours:

```python
def cleanup_aged_artifacts():
    """Remove artifacts past retention period."""
    for run_id in list_runs():
        run_age = days_since_created(run_id)

        # Full run cleanup
        if run_age > 30 and not has_exception(run_id):
            archive_or_delete(run_id)
            continue

        # Transcript cleanup (more aggressive)
        if run_age > 7:
            delete_transcripts(run_id)

        # Receipt archival (longer retention)
        if run_age > 90:
            archive_receipts(run_id)
```

### Archive vs Delete

| Action | When | What Happens |
|--------|------|--------------|
| **Delete** | Past retention, no exception | Permanent removal |
| **Archive** | Past active period, audit needed | Compress and move to cold storage |
| **Retain** | Exception applies | Keep until exception cleared |

### Compression for Archives

Archived data uses:
- gzip for JSON/JSONL files
- tar.gz for directory bundles
- Naming: `<run-id>-archive-<date>.tar.gz`

Archive location:
```
swarm/archives/<year>/<month>/<run-id>-archive.tar.gz
```

## The Rule

> Artifacts have finite lifetimes. Define retention upfront.
> Automate cleanup. Never delete git history.

---

## See Also
- [data-retention.md](./data-retention.md) - Overview and commands
- [data-retention-exceptions.md](./data-retention-exceptions.md) - Exception handling
- [data-retention-privacy.md](./data-retention-privacy.md) - Privacy and PII
