# Rollback Guide

When something breaks, choose the right rollback method.

## Methods

| Type | When | Notes |
|------|------|-------|
| Git Revert | Undo on upstream | Creates new commit, preserves history |
| Git Reset | Shadow fork only | Rewrites history, NEVER on upstream |
| Feature Disable | Fastest response | Runtime flag, code stays deployed |
| Data Rollback | Corruption | Restore from backup, reconcile carefully |

## Decision Tree

- Production broken + can disable via flag → Feature Disable
- Production broken + no flag → Git Revert
- Shadow fork issue → Git Reset
- Data corruption → Data Rollback (last resort)

## Prevention

- Staged rollouts: 1% → 5% → 25% → 100%
- Canary deployments
- Feature flags for new functionality
- Backward-compatible migrations

## Pre-Deploy Checklist

- [ ] Revert commit identified
- [ ] Feature flag exists
- [ ] DB migrations are backward-compatible
- [ ] Monitoring alerts configured
- [ ] Rollback tested in staging
