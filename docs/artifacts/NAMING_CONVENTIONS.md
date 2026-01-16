# Artifact Naming Conventions

Artifacts are addresses. Stable paths beat explanation.

## Path Structure

```
RUN_BASE/<flow>/<step>/
├── receipts/<step>-<agent>.json
├── handoffs/<step>-<agent>.json
├── logs/<step>.jsonl
└── llm/<step>-<agent>-<engine>.jsonl
```

## Rules

- Use lower_snake_case, no spaces
- Evidence goes to `receipts/` and `build/`
- Prefer `.jsonl` for append-only logs; `.json` for complete objects
- Never rename evidence files after publishing a receipt

See also: [ROUTING_PROTOCOL.md](../ROUTING_PROTOCOL.md)
