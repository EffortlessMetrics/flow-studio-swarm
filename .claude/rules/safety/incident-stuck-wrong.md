# Stuck Run and Wrong Output Playbooks

## Purpose

Step-by-step debugging procedures for runs that stopped progressing (stuck) or completed with incorrect results (wrong output).

## The Rule

> Follow the evidence trail. Routing logs show the decisions.
> Scent trail shows prior assumptions. When in doubt, check the artifacts before asking the agent.

---

## Stuck Run

A run that stopped progressing. No new receipts are being generated, but no explicit failure.

### Diagnostic Procedure

```
1. Identify the stuck step
   → Which step has no receipt or incomplete receipt?

2. Check for BLOCKED status
   → RUN_BASE/<flow>/handoffs/*.json
   → Look for "status": "BLOCKED"

3. Check for missing inputs
   → Does previous step's output exist?
   → Are required artifacts present?

4. Check routing decisions
   → RUN_BASE/<flow>/routing/decisions.jsonl
   → Was there an ESCALATE that wasn't handled?

5. Check iteration limits
   → Microloop at max iterations?
   → Same failure signature repeated?
```

### Common Causes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| BLOCKED status | Missing required input | Provide input or fix previous step |
| ESCALATE in routing log | Human decision needed | Make decision, document, continue |
| Max iterations reached | Microloop exhausted | Check if detour would help, or adjust limit |
| Same failure signature 2x | Known failure pattern | Route to appropriate detour (lint-fix, etc.) |
| No handoff envelope | Step crashed before finalization | Check transcript for errors |

### Resuming a Stuck Run

```bash
# If previous steps succeeded, resume from stuck step
make stepwise-<flow> RUN_ID=<run-id> START_STEP=<stuck-step>

# If environment issue fixed, retry the step
make stepwise-retry RUN_ID=<run-id> FLOW=<flow> STEP=<step>
```

---

## Wrong Output

The run completed but produced incorrect results. Tests may pass but behavior is wrong.

### Diagnostic Procedure

```
1. Check evidence panel
   → Do all metrics agree?
   → Any "not measured" that should have been measured?

2. Verify inputs were correct
   → Check previous flow outputs
   → Check teaching notes loaded correctly

3. Check scent trail
   → RUN_BASE/<flow>/scent_trail.json
   → Were prior decisions correct?

4. Check assumptions
   → Handoff envelope assumptions[] field
   → Were assumptions valid?

5. Compare to spec
   → Does output match requirements?
   → Were requirements correctly interpreted?
```

### Common Causes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Panel metrics disagree | Hollow tests or gaming | Add mutation testing, improve assertions |
| Wrong assumptions | Ambiguous requirements | Clarify requirements, re-run from Signal |
| Scent trail shows bad decision | Early step went wrong | Re-run from the step with the bad decision |
| Teaching notes not loaded | Context budget exceeded | Increase budget or prioritize context |
| Spec mismatch | Requirements changed | Update requirements, re-plan |

### Verification Checklist

- [ ] Evidence panel metrics all agree
- [ ] Assumptions documented and valid
- [ ] Scent trail decisions are sound
- [ ] Output matches current spec
- [ ] No "not measured" gaps for critical paths

---

## Quick Reference: Artifact Locations

| Artifact | Path | Contains |
|----------|------|----------|
| Handoff envelopes | `RUN_BASE/<flow>/handoffs/<step>-<agent>.json` | Summary, concerns, assumptions, routing |
| Routing decisions | `RUN_BASE/<flow>/routing/decisions.jsonl` | All routing choices |
| Scent trail | `RUN_BASE/<flow>/scent_trail.json` | Decision provenance |
| Step receipts | `RUN_BASE/<flow>/receipts/<step>-<agent>.json` | Status, tokens, duration, evidence |

---

## See Also

- [incident-response.md](./incident-response.md) - Core incident response protocol (severity levels, containment, post-mortems)
- [incident-failed-run.md](./incident-failed-run.md) - Failed run playbook
- [../artifacts/handoff-protocol.md](../artifacts/handoff-protocol.md) - Envelope structure
- [../artifacts/scent-trail.md](../artifacts/scent-trail.md) - Decision provenance
- [../execution/detour-catalog.md](../execution/detour-catalog.md) - Known fix patterns
