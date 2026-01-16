# Resume Protocol

Every step leaves a checkpoint. Runs are resumable by default.

## Checkpoint Invariant

After each step completes:
1. Receipt written to disk
2. Artifacts persisted
3. Handoff envelope committed
4. State is resumable

## Valid Checkpoint Exists When

```
RUN_BASE/<flow>/receipts/<step_id>-<agent>.json  # exists
RUN_BASE/<flow>/handoffs/<step_id>-<agent>.json  # exists (if finalized)
```

## Resume Logic

- Last step succeeded → resume from next step
- Last step failed → retry that step

## On Partial Failure

- Files written to disk → preserved
- In-memory state → lost
- Uncommitted handoff → lost
- Recovery: retry step from scratch or escalate

## Rules

- Steps should be idempotent (safe to run twice)
- Checkpoint after each step, not at flow end
