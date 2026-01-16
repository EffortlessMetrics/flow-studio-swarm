---
name: rollback-execution
description: Execute rollbacks safely. Use when reverting deployments, commits, or configuration changes.
---
# Rollback Execution

1. Identify rollback type needed (git revert, feature flag, data restore).
2. For git revert: Create revert commit, preserve history.
3. For feature flag: Toggle flag, verify disabled behavior.
4. For data rollback: Restore from backup, reconcile carefully.
5. Verify service restored (health checks, smoke tests).
6. Document rollback with evidence paths.
