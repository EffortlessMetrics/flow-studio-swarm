---
name: run-resume
description: Resume interrupted runs from last checkpoint in RUN_BASE. Use when continuing failed or interrupted flow execution, restoring from receipts and handoffs.
---
# Run Resume

1. Find last checkpoint: `RUN_BASE/<flow>/receipts/<step>-<agent>.json`.
2. Verify checkpoint validity (receipt + handoff both exist).
3. If last step succeeded: Resume from next step.
4. If last step failed: Retry that step from scratch.
5. Restore context from artifacts (not conversation history).
6. Continue flow execution with fresh context.
