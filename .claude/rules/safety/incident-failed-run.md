# Failed Run Playbook

## Purpose

Step-by-step debugging procedure for runs that terminated with an error. A failed run shows `"status": "failed"` in the step receipt.

## The Rule

> Follow the evidence trail. Receipts show what happened.
> Transcripts show why. When in doubt, check the artifacts before asking the agent.

## Diagnostic Procedure

```
1. Check receipt for failing step
   → RUN_BASE/<flow>/receipts/<step>-<agent>.json

2. Check status field
   → "succeeded" | "failed" | "interrupted"

3. If failed, check error field
   → Error message and stack trace

4. Check transcript for context
   → RUN_BASE/<flow>/llm/<step>-<agent>-<engine>.jsonl

5. Check handoff envelope
   → RUN_BASE/<flow>/handoffs/<step>-<agent>.json
   → Look at concerns[] and routing.reason
```

## Common Causes

| Error Pattern | Likely Cause | Fix |
|---------------|--------------|-----|
| `ModuleNotFoundError` | Missing dependency | Add to requirements, re-run |
| `FileNotFoundError` on input | Previous step didn't produce output | Check previous step receipt |
| `TimeoutError` | Step exceeded time limit | Increase timeout or simplify step |
| `ValidationError` | Malformed output from agent | Check teaching notes, adjust prompt |
| Exit code non-zero | Tool command failed | Check command output in receipt |

## Verification After Fix

```bash
# Re-run the failing flow
make stepwise-<flow> RUN_ID=<new-run-id>

# Verify receipt shows success
cat RUN_BASE/<flow>/receipts/<step>-<agent>.json

# Check evidence panel
# All metrics should agree
```

## Quick Reference: Artifact Locations

| Artifact | Path | Contains |
|----------|------|----------|
| Step receipts | `RUN_BASE/<flow>/receipts/<step>-<agent>.json` | Status, tokens, duration, evidence |
| Handoff envelopes | `RUN_BASE/<flow>/handoffs/<step>-<agent>.json` | Summary, concerns, assumptions, routing |
| Transcripts | `RUN_BASE/<flow>/llm/<step>-<agent>-<engine>.jsonl` | Full LLM conversation |
| Step logs | `RUN_BASE/<flow>/logs/<step>.jsonl` | Execution events |

---

## See Also

- [incident-response.md](./incident-response.md) - Core incident response protocol (severity levels, containment, post-mortems)
- [incident-stuck-wrong.md](./incident-stuck-wrong.md) - Stuck runs and wrong output playbooks
- [../artifacts/receipt-schema.md](../artifacts/receipt-schema.md) - Receipt structure
- [../execution/resume-protocol.md](../execution/resume-protocol.md) - Resuming failed runs
