# Rollback Prevention

## Purpose

Design systems so rollbacks are fast, safe, and low-risk. Prevention is better than cure, but when cure is needed, make it painless.

## The Rule

> Design for rollback from the start.
> Prefer reversible actions. Build with the assumption that rollback will be needed.

## Staged Rollouts

Deploy incrementally to limit blast radius.

```bash
# Deploy to 1% first
kubectl set image deployment/app app=image:v2 --record
kubectl rollout pause deployment/app

# Check metrics, then continue
kubectl rollout resume deployment/app
```

**Benefits:**
- Catch issues before full exposure
- Easy to halt and revert
- Real production traffic for validation

## Canary Deployments

Run new version alongside old with traffic splitting.

**Process:**
1. Deploy new version alongside old
2. Route small percentage of traffic to new
3. Compare error rates
4. Full rollout only if metrics are healthy

**Traffic progression:**
```
1% → monitor → 5% → monitor → 25% → monitor → 100%
```

**Rollback:** Route 100% back to old version instantly.

## Feature Flags for Risky Changes

Wrap risky code in flags for instant disable capability.

```python
# Wrap risky code in flags
if feature_flags.is_enabled("new_payment_flow"):
    return new_payment_flow(request)
else:
    return legacy_payment_flow(request)
```

**Benefits:**
- Deploy code without activating it
- Instant disable without deployment
- Gradual rollout to user segments
- A/B testing built-in

**Requirements:**
- Flag service must be external to deployment
- Flag evaluation must be fast (cached)
- Default to safe/old behavior when flag service unavailable

## Database Migration Safety

Only backward-compatible migrations in the deploy path.

```sql
-- Backward-compatible migrations only
-- Add column (safe):
ALTER TABLE users ADD COLUMN new_field TEXT;

-- Drop column (unsafe, do later):
-- ALTER TABLE users DROP COLUMN old_field;
```

### Safe Migration Pattern

```
Deploy 1: Add new column (nullable)
Deploy 2: Start writing to both columns
Deploy 3: Backfill old data to new column
Deploy 4: Start reading from new column
Deploy 5: Stop writing to old column
Deploy 6: Drop old column (separate, delayed)
```

**Key principle:** Old code must work with new schema. New code must work with old schema. This allows rollback at any point.

### Dangerous Migrations

| Migration | Risk | Alternative |
|-----------|------|-------------|
| DROP COLUMN | Data loss | Soft deprecate, drop later |
| RENAME COLUMN | Breaks old code | Add new, migrate, drop old |
| CHANGE TYPE | May truncate | Add new column, migrate |
| DROP TABLE | Data loss | Archive, drop much later |

## Rollback Readiness Checklist

Before every deployment, verify:

- [ ] **Revert commit identified** - Know what SHA to revert if needed
- [ ] **Feature flag exists** - For new functionality, can disable instantly
- [ ] **Database migrations are backward-compatible** - Old code works with new schema
- [ ] **Monitoring alerts configured** - Will know quickly if something breaks
- [ ] **On-call engineer aware** - Someone is watching during deploy
- [ ] **Rollback tested** - Have actually tried the rollback in staging

## Post-Rollback Checklist

After executing a rollback:

### 1. Verify Rollback Succeeded
- [ ] CI is green
- [ ] Health checks pass
- [ ] Affected functionality works
- [ ] Error rates returned to baseline
- [ ] No new errors in logs

```bash
# Check CI status
gh run list --limit 5

# Check for errors
grep -i error /var/log/app/current.log | tail -20
```

### 2. Communicate Status
- [ ] Update incident channel
- [ ] Notify affected teams
- [ ] Update status page (if public-facing)

### 3. Post-Mortem
- [ ] Schedule post-mortem within 48 hours
- [ ] Document: what happened, why, how fixed, how to prevent
- [ ] Create follow-up tickets

## Anti-Patterns

### Deploy Without Rollback Plan

**Problem:** When things break, panic ensues.

**Fix:** Always know the revert SHA before deploying.

### Breaking Database Migrations

**Problem:** Can't roll back code because schema changed.

**Fix:** Expand-contract pattern. Never break backward compatibility.

### No Feature Flags on Risky Changes

**Problem:** Must redeploy to disable broken feature.

**Fix:** Wrap new features in flags. Instant disable capability.

### Big Bang Deployments

**Problem:** 100% of users hit issues simultaneously.

**Fix:** Staged rollouts. Start with 1%, watch metrics.

---

## See Also
- [rollback-types.md](./rollback-types.md) - The four rollback methods and when to use each
- [git-safety.md](./git-safety.md) - Git operations by zone
- [incident-response.md](./incident-response.md) - Incident response protocol
- [boundary-automation.md](./boundary-automation.md) - Publish gate checks
