# Observability Placement: Correlation and Location

Where logs go and how to correlate them across steps, flows, and runs.

## Trace Correlation

### Run-Level Correlation

`run_id` ties all logs from a single run together:

```bash
# Find all logs for a run
grep '"run_id":"abc123"' RUN_BASE/*/logs/*.jsonl
```

All logs from the same run share the same `run_id`. This is the primary correlation key.

### Step-Level Correlation

`step_id` correlates within a step:

```bash
# Find all logs for a step
grep '"step_id":"step-3"' RUN_BASE/build/logs/*.jsonl
```

### Parent/Child for Subagent Calls

When a step spawns subagents, use parent/child linking:

```json
{
  "timestamp": "2024-01-15T10:30:02.000Z",
  "level": "INFO",
  "run_id": "abc123",
  "flow_key": "build",
  "step_id": "step-3",
  "agent_key": "code-implementer",
  "message": "Spawning subagent: explore",
  "event": "subagent_spawn",
  "child_step_id": "step-3-explore-1"
}
```

The child logs with:

```json
{
  "step_id": "step-3-explore-1",
  "parent_step_id": "step-3",
  ...
}
```

### Correlation Hierarchy

```
run_id (run-level)
  └── flow_key (flow-level)
       └── step_id (step-level)
            └── child_step_id (subagent-level)
```

## Log Locations

### Per-Step Logs

Logs are written per-step to:

```
RUN_BASE/<flow>/logs/<step_id>.jsonl
```

Example:
```
swarm/runs/abc123/build/logs/step-3.jsonl
swarm/runs/abc123/build/logs/step-4.jsonl
```

### Aggregated Logs

For flow-level view:

```
RUN_BASE/<flow>/logs/flow.jsonl
```

Contains all step logs concatenated in order.

### Run-Level Index

For cross-flow view:

```
RUN_BASE/logs/run.jsonl
```

Contains key events (step_start, step_end, routing_decision) from all flows.

### Location Summary

| Scope | Path | Contents |
|-------|------|----------|
| Step | `RUN_BASE/<flow>/logs/<step_id>.jsonl` | All logs from one step |
| Flow | `RUN_BASE/<flow>/logs/flow.jsonl` | All step logs concatenated |
| Run | `RUN_BASE/logs/run.jsonl` | Key events from all flows |

## Log Rotation

### During Execution

Within a run, logs are append-only. No rotation during execution.

### After Completion

After run completion:
- Compress logs older than 7 days
- Archive to cold storage after 30 days
- Delete after retention period (configurable)

### Retention Defaults

| Artifact | Retention | Notes |
|----------|-----------|-------|
| Per-step logs | 30 days | Debugging window |
| Aggregated flow logs | 30 days | Same as step logs |
| Run-level index | 90 days | Audit trail |
| Archived logs | Per policy | Cold storage |

## Querying Patterns

### Find All Logs for a Run
```bash
grep '"run_id":"abc123"' RUN_BASE/*/logs/*.jsonl
```

### Find Errors in a Run
```bash
grep '"level":"ERROR"' RUN_BASE/*/logs/*.jsonl | grep '"run_id":"abc123"'
```

### Find Step Timeline
```bash
grep -E '"event":"step_(start|end)"' RUN_BASE/build/logs/*.jsonl
```

### Find Routing Decisions
```bash
grep '"event":"routing_decision"' RUN_BASE/*/logs/*.jsonl
```

### Find Token Warnings
```bash
grep '"event":"token_warning"' RUN_BASE/*/logs/*.jsonl
```

## The Rule

> `run_id` ties everything together. Step logs are the primary unit.
> Aggregated logs enable flow-level and run-level views.
> Rotation happens after completion, not during.

---

## See Also
- [observability-schema.md](./observability-schema.md) - Log format and fields
- [observability-content.md](./observability-content.md) - What to log
- [data-retention.md](./data-retention.md) - Full retention policy
