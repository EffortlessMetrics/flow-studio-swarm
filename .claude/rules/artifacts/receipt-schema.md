# Receipt Schema

Receipts are the audit trail.

## Required Fields
- engine, mode, provider
- step_id, flow_key, run_id, agent_key
- started_at, completed_at, duration_ms
- status: succeeded | failed
- tokens: {prompt, completion, total}

## Evidence Binding
Claims require evidence pointers:
```json
{"tests": {"measured": true, "passed": 42, "evidence_path": "..."}}
```
Not measured: `{"measured": false, "reason": "..."}`

## Placement
`RUN_BASE/<flow>/receipts/<step_id>-<agent_key>.json`

> Docs: docs/artifacts/RECEIPT_SCHEMA.md
