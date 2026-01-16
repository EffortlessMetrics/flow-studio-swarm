# Failed Runs Troubleshooting

Follow the evidence trail.

## Diagnostic Path

1. Receipt: `RUN_BASE/<flow>/receipts/<step>-<agent>.json`
2. Status field: succeeded | failed | interrupted
3. Error field if failed
4. Transcript: `RUN_BASE/<flow>/llm/<step>-<agent>-<engine>.jsonl`
5. Handoff envelope for concerns/routing

## Common Patterns

| Pattern | Likely Cause | Fix |
|---------|--------------|-----|
| ModuleNotFoundError | Missing dep | Add to requirements |
| FileNotFoundError on input | Previous step failed | Check previous step |
| TimeoutError | Step too slow | Increase timeout or split |
| Same error twice | Not learning | Route to detour |

## Stuck Run Diagnosis

1. Identify stuck step (no receipt)
2. Check for BLOCKED in handoff
3. Check for missing inputs
4. Check if microloop hit iteration limit

## Wrong Output Diagnosis

1. Check evidence panel (do metrics agree?)
2. Check assumptions in envelope
3. Compare output to spec
4. Look for scope drift

## Rules

- Check artifacts before asking the agent
- Trust physics (logs, exit codes), not claims
- If signature repeats, route to detour
