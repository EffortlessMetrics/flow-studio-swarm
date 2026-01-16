# Failed Run Playbook

Follow the evidence trail.

## Diagnostic Path
1. Receipt: `RUN_BASE/<flow>/receipts/<step>-<agent>.json`
2. Status field: succeeded | failed | interrupted
3. Error field if failed
4. Transcript: `RUN_BASE/<flow>/llm/<step>-<agent>-<engine>.jsonl`
5. Handoff envelope for concerns/routing

## Common Causes
| Pattern | Fix |
|---------|-----|
| ModuleNotFoundError | Add to requirements |
| FileNotFoundError on input | Check previous step |
| TimeoutError | Increase timeout |

> Skill: heal_selftest
> Docs: docs/troubleshooting/FAILED_RUNS.md
