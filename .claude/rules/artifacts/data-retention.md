# Data Retention: Artifact Lifecycle Management

Artifacts have finite lifetimes. This rule defines how long to keep what, and when to clean up.

## Topic Files

Data retention is split into focused concerns:

| File | Purpose |
|------|---------|
| [data-retention-lifecycle.md](./data-retention-lifecycle.md) | Retention periods, cleanup policies, archive vs delete |
| [data-retention-exceptions.md](./data-retention-exceptions.md) | Open PR, incident, and compliance hold exceptions |
| [data-retention-privacy.md](./data-retention-privacy.md) | PII handling, deletion requests, anonymization |

## Storage Costs Summary

| Component | Typical Size | Notes |
|-----------|--------------|-------|
| Receipts | 50-100 KB | JSON, highly compressible |
| Transcripts | 1-10 MB | JSONL, largest component |
| Handoffs | 20-50 KB | JSON, structured |
| Routing logs | 10-30 KB | JSONL, append-only |
| Other artifacts | 100-500 KB | Varies by flow |
| **Total per run** | **2-15 MB** | Uncompressed |
| **Compressed** | **200 KB - 2 MB** | ~10:1 ratio |

### Cost Triggers

| Threshold | Action |
|-----------|--------|
| > 1 GB total | Review oldest runs |
| > 100 runs | Enforce retention |
| > 10 GB total | Emergency cleanup |
| > 30 days old + no exception | Auto-cleanup eligible |

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Retention periods | Designed | See lifecycle file |
| Cleanup job | Designed | Needs implementation |
| Exception handling | Designed | Needs implementation |
| Storage monitoring | Supported | Manual commands below |
| Anonymization | Designed | Needs implementation |

## The Rule

> Artifacts have finite lifetimes. Define retention upfront.
> Automate cleanup. Honor exceptions. Never delete git history.

## Commands

### Check Retention Status
```bash
make retention-status  # Show aged artifacts and exceptions
```

### Manual Cleanup
```bash
make cleanup-aged      # Remove artifacts past retention
make cleanup-transcripts  # Remove transcripts >7 days
```

### Apply Exception
```bash
make retention-hold RUN_ID=abc123 REASON="incident"
make retention-release RUN_ID=abc123
```

---

## See Also
- [receipt-schema.md](./receipt-schema.md) - Receipt structure
- [off-road-logging.md](./off-road-logging.md) - Routing audit trail
- [handoff-protocol.md](./handoff-protocol.md) - Handoff envelope structure
