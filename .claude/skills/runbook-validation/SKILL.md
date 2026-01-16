---
name: runbook-validation
description: Validate runbooks are executable and complete. Use when reviewing or testing runbook quality.
---
# Runbook Validation

1. Check all six sections present (purpose, prereqs, steps, verify, rollback, troubleshooting).
2. Verify every step has expected output specified.
3. Confirm decision points are explicitly documented.
4. Test execution yourself or with unfamiliar person.
5. Check idempotence: running twice causes no harm.
6. Update based on friction (every question → documentation).
