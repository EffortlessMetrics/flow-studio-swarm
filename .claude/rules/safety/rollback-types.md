# Rollback Types

## Purpose

When something breaks, choose the right rollback method based on where you are (shadow fork vs upstream) and what broke (code, feature, data).

## The Rule

> Prefer reversible actions. When in doubt, revert first, investigate second.
> Git Revert for upstream. Git Reset for shadow fork only. Feature Disable for fastest response.

## Rollback Triggers

### When to Roll Back Immediately

| Trigger | Severity | Response Time |
|---------|----------|---------------|
| **Failed deployment** | CI red after merge | < 15 minutes |
| **Production incident** | SEV1 (service down) | < 5 minutes |
| **Production incident** | SEV2 (degraded) | < 30 minutes |
| **Security issue** | Exposed secrets | IMMEDIATE |
| **Security issue** | Vulnerability in prod | < 1 hour |
| **Bad merge** | Broke functionality | < 1 hour |

### How to Identify the Bad Change

```bash
# Find the merge commit
git log --oneline --merges -10

# Show what changed in a commit
git show <sha> --stat

# Find when a file was last modified
git log --oneline -5 -- path/to/broken/file

# Compare current state to known-good
git diff <known-good-sha> HEAD -- path/to/file
```

## The Four Rollback Types

### 1. Git Revert (Preferred for Upstream)

Creates a new commit that undoes changes. **Preferred method for upstream/production.**

```bash
# Revert a single commit
git revert <sha>

# Revert a merge commit (specify which parent to keep)
git revert -m 1 <merge-sha>

# Revert multiple commits (oldest to newest)
git revert <oldest-sha>^..<newest-sha>

# Push the revert
git push origin main
```

**When to use:**
- Any rollback on upstream/main
- Shared branches
- When you want to preserve history

**Advantages:**
- Preserves full history
- Safe for shared branches
- Easy to "revert the revert" later
- Creates audit trail

### 2. Git Reset (Shadow Fork Only)

Rewrites history by moving HEAD backward. **ONLY use in shadow fork, NEVER on upstream.**

```bash
# In shadow fork only:
git reset --hard <sha>
git push --force origin feature-branch
```

**When to use:**
- Inside the shadow fork during Flows 1-5
- Cleaning up messy work before publish

**BLOCKED on upstream:**
```bash
# NEVER do this to upstream:
git reset --hard <sha>
git push --force upstream main   # BLOCKED
```

### 3. Feature Disable (Fastest Response)

Keep code deployed but disable at runtime. **Fastest way to stop the bleeding.**

```bash
# Via environment variable
export FEATURE_X_ENABLED=false

# Via config file
echo '{"feature_x": false}' > config/features.json

# Via feature flag service
curl -X POST https://flags.example.com/api/flags/feature_x/disable
```

**When to use:**
- Fastest possible response needed (SEV1)
- Code itself is fine, just behavior is wrong
- Need time to investigate root cause

**Requirements:**
- Feature must have been built with disable capability
- Config/flag must be external to the codebase

### 4. Data Rollback (Last Resort)

Restore from backup when data is corrupted. **Requires careful reconciliation.**

```bash
# Stop writes to affected tables
# (Application-specific commands)

# Restore from backup
pg_restore -d database backup_file.dump

# Or point-in-time recovery
pg_restore -d database --target-time="2024-01-15 10:00:00"
```

**When to use:**
- Data corruption
- Cascading deletes
- Schema migration failure

**CRITICAL:** Requires reconciliation of any data written between backup and now.

## Decision Tree

```
Is production broken?
│
├─ YES: Is it a security issue?
│       │
│       ├─ YES (secrets exposed) → IMMEDIATE: Rotate secrets + Git Revert
│       │
│       └─ NO → Can you disable via feature flag?
│               │
│               ├─ YES → Feature Disable (fastest)
│               │
│               └─ NO → Git Revert
│
└─ NO: Is it a shadow fork issue?
       │
       ├─ YES → Git Reset (fork only)
       │
       └─ NO → Plan fix in next release
```

## What Cannot Be Rolled Back

Some actions are irreversible. Plan accordingly.

| Action | Why Irreversible | Mitigation |
|--------|------------------|------------|
| **Sent notifications** | Emails, SMS, push already delivered | Test in staging, staged rollout |
| **External API calls** | Third-party state changed | Idempotency keys, dry-run mode |
| **Published packages** | npm, PyPI don't allow re-publish of same version | Bump version, deprecate bad version |
| **Deleted data** | Gone without backup | Soft deletes, backups, retention policies |
| **Leaked secrets** | Attacker may have copied | Rotate immediately, assume compromised |

---

## See Also
- [rollback-prevention.md](./rollback-prevention.md) - Design for rollback from the start
- [git-safety.md](./git-safety.md) - Git operations by zone
- [boundary-automation.md](./boundary-automation.md) - Publish gate checks
- [incident-response.md](./incident-response.md) - Incident response protocol
