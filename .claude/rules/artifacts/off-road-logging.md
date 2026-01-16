# Off-Road Logging

Every off-road decision leaves a trace.

## What Gets Logged
- All non-CONTINUE routing decisions
- All flow injections
- All node injections
- All escalations

Golden path (CONTINUE) is implicit. Deviations are explicit.

## Artifact Locations
```
RUN_BASE/<flow>/routing/
├── decisions.jsonl          # Append-only decision log
├── injections/              # Flow/node injection records
└── proposals/               # Graph extension proposals
```

## Decision Log Entry
- timestamp, run_id, flow_key, step_id
- decision: LOOP | DETOUR | INJECT_FLOW | ESCALATE | TERMINATE
- reason: human-readable justification
- forensic_summary: compact metrics that informed decision

## The Rule
- JSONL for decisions (append-only, streamable)
- JSON for injection records (complete objects)
- Audit trail is append-only, never modified

> Docs: docs/execution/ROUTING_PROTOCOL.md
