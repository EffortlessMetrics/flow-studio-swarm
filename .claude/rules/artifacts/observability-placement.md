# Observability Placement

`run_id` ties everything together. Step logs are the primary unit.

## Correlation Hierarchy
```
run_id (run-level)
  └── flow_key (flow-level)
       └── step_id (step-level)
            └── child_step_id (subagent-level)
```

## Log Locations
| Scope | Path |
|-------|------|
| Step | `RUN_BASE/<flow>/logs/<step_id>.jsonl` |
| Flow | `RUN_BASE/<flow>/logs/flow.jsonl` |
| Run | `RUN_BASE/logs/run.jsonl` |

## Rotation
- During execution: append-only, no rotation
- After completion: compress > 7 days, archive > 30 days

## The Rule
- `run_id` correlates across everything
- Step logs are primary, aggregated logs enable flow/run views
- Rotation happens after completion, not during

> Docs: docs/artifacts/OBSERVABILITY.md
