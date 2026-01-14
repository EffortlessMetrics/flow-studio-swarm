# Data Retention Exceptions

Some artifacts must be retained beyond standard periods. This rule defines exception types and priority.

## Exception Types

### Open PR References

Runs referenced by open PRs are retained until PR closes:

```yaml
exception:
  type: open_pr
  pr_number: 123
  run_ids: ["abc123", "def456"]
  expires_when: pr_closed
```

### Incident References

Runs with incidents are retained until post-mortem completes:

```yaml
exception:
  type: incident
  incident_id: "INC-2024-001"
  run_ids: ["abc123"]
  expires_when: postmortem_complete
  owner: "oncall@example.com"
```

### Compliance Holds

Legal or compliance holds override all retention:

```yaml
exception:
  type: compliance_hold
  hold_id: "LEGAL-2024-001"
  run_ids: ["*"]  # Can be wildcard
  expires_when: manual_release
  authority: "legal@example.com"
```

## Exception Priority

When exceptions conflict, higher priority wins:

| Priority | Type | Behavior |
|----------|------|----------|
| 1 (highest) | Compliance holds | Never delete |
| 2 | Incident references | Keep until cleared |
| 3 | Open PR references | Keep until PR closed |
| 4 (lowest) | Standard retention | Normal cleanup |

## Exception Schema

All exceptions share a common structure:

```yaml
exception:
  type: open_pr | incident | compliance_hold
  run_ids: ["string"]           # Affected runs (* for wildcard)
  expires_when: string          # Condition for expiration
  created_at: "ISO8601"         # When exception was created
  created_by: "string"          # Who created the exception
  notes: "string"               # Optional context
```

## The Rule

> Honor exceptions before cleanup.
> Compliance holds are absolute.
> Document why each exception exists.

---

## See Also
- [data-retention.md](./data-retention.md) - Overview and commands
- [data-retention-lifecycle.md](./data-retention-lifecycle.md) - Retention periods
- [data-retention-privacy.md](./data-retention-privacy.md) - Privacy and PII
