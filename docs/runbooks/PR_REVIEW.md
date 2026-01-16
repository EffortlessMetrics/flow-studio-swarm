# PR Review Runbook

## Purpose

Review pull requests against intent, evidence, and risk.

## Prerequisites

- PR is in Ready state (not Draft)
- All CI checks have completed
- Intent source exists (spec, ADR, work plan)

## Steps

1. **Verify intent alignment**: Check changes match spec/ADR/work plan
2. **Verify evidence**: Require exit codes + logs + artifacts for all claims
3. **Check bounded scope**: Reject opportunistic refactors
4. **Identify hotspots**: Mark risks with file:line references
5. **Route concerns**: Fix-forward with UNVERIFIED or BLOCK if critical

## Verification

- [ ] All claims have evidence paths
- [ ] No scope creep
- [ ] Hotspots documented
- [ ] Status is VERIFIED / UNVERIFIED / BLOCKED

## Output

```json
{
  "status": "VERIFIED | UNVERIFIED | BLOCKED",
  "evidence": {"present": [...], "missing": [...]},
  "hotspots": [{"file": "...", "line": ..., "risk": "..."}],
  "recommendation": "..."
}
```

## Rollback

N/A - Review is non-destructive.
