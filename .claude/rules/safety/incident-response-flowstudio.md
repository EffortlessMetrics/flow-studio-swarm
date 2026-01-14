# Flow Studio Incident Playbooks

**Operational playbooks for diagnosing and resolving Flow Studio specific incidents.**

This document provides step-by-step debugging procedures for common Flow Studio failure modes. For the general incident response protocol (severity levels, containment, post-mortems), see [incident-response.md](./incident-response.md).

## Failed Run

A run that terminated with an error. The step receipt shows `"status": "failed"`.

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

### Common Causes

| Error Pattern | Likely Cause | Fix |
|---------------|--------------|-----|
| `ModuleNotFoundError` | Missing dependency | Add to requirements, re-run |
| `FileNotFoundError` on input | Previous step didn't produce output | Check previous step receipt |
| `TimeoutError` | Step exceeded time limit | Increase timeout or simplify step |
| `ValidationError` | Malformed output from agent | Check teaching notes, adjust prompt |
| Exit code non-zero | Tool command failed | Check command output in receipt |

### Verification After Fix

```bash
# Re-run the failing flow
make stepwise-<flow> RUN_ID=<new-run-id>

# Verify receipt shows success
cat RUN_BASE/<flow>/receipts/<step>-<agent>.json

# Check evidence panel
# All metrics should agree
```

## Stuck Run

A run that stopped progressing. No new receipts are being generated, but no explicit failure.

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

## Wrong Output

The run completed but produced incorrect results. Tests may pass but behavior is wrong.

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

## Security Incident

Secrets, credentials, or sensitive data may have been exposed.

```
1. IMMEDIATE: Revoke any exposed credentials
   → Rotate API keys, tokens, passwords

2. Assess scope
   → What was exposed?
   → For how long?
   → Who had access?

3. Check boundary logs
   → Did secrets scan run?
   → What slipped through?

4. Audit recent publishes
   → git log of upstream pushes
   → Any suspicious commits?

5. Notify stakeholders
   → Security team
   → Affected users
   → Legal if required
```

### Immediate Actions by Secret Type

| Secret Type | Revocation Method | Rotation |
|-------------|-------------------|----------|
| OpenAI API key | Dashboard > API Keys | Generate new, update env |
| Anthropic API key | Console > API Keys | Generate new, update env |
| GitHub token | Settings > Developer > Tokens | Regenerate, update env |
| AWS credentials | IAM > Security credentials | Rotate access key |
| Database password | Database admin console | Change password, update connection strings |

### Post-Containment

```bash
# Check if secret is in git history
git log -p --all -S 'sk-ant-' | head -50

# If in history, assess if pushed to upstream
git log --remotes --oneline | head -20

# Check boundary scan logs for the run
cat RUN_BASE/<flow>/boundary_scan.log
```

### Notification Template

```markdown
## Security Incident Notification

**Severity**: SEV1 / SEV2
**Discovered**: <timestamp>
**Type**: <credential exposure / data leak / unauthorized access>

### What Happened
<brief description>

### Immediate Actions Taken
- [ ] Credentials revoked at <time>
- [ ] New credentials generated at <time>
- [ ] Systems updated at <time>

### Scope
- **What was exposed**: <details>
- **Duration of exposure**: <start> to <end>
- **Potential impact**: <assessment>

### Next Steps
<action items with owners>
```

## Action Item Template

Every action item from incident response must have:

```markdown
- [ ] **Action**: <specific action to take>
  - **Owner**: <person responsible>
  - **Deadline**: <date>
  - **Verification**: <how we know it's done>
  - **Status**: pending | in-progress | complete
```

### Example Action Items

```markdown
- [ ] **Action**: Add pre-commit hook for secret detection
  - **Owner**: Platform Team
  - **Deadline**: 2024-01-20
  - **Verification**: Hook blocks commit containing test secret pattern
  - **Status**: pending

- [ ] **Action**: Rotate all API keys used in affected flow
  - **Owner**: SRE
  - **Deadline**: 2024-01-16
  - **Verification**: Old keys return 401, new keys work
  - **Status**: complete
```

## Quick Reference: Artifact Locations

| Artifact | Path | Contains |
|----------|------|----------|
| Step receipts | `RUN_BASE/<flow>/receipts/<step>-<agent>.json` | Status, tokens, duration, evidence |
| Handoff envelopes | `RUN_BASE/<flow>/handoffs/<step>-<agent>.json` | Summary, concerns, assumptions, routing |
| Transcripts | `RUN_BASE/<flow>/llm/<step>-<agent>-<engine>.jsonl` | Full LLM conversation |
| Routing decisions | `RUN_BASE/<flow>/routing/decisions.jsonl` | All routing choices |
| Scent trail | `RUN_BASE/<flow>/scent_trail.json` | Decision provenance |
| Step logs | `RUN_BASE/<flow>/logs/<step>.jsonl` | Execution events |

## The Rule

> Follow the evidence trail. Receipts show what happened.
> Transcripts show why. Routing logs show the decisions.
> When in doubt, check the artifacts before asking the agent.

---

## See Also
- [incident-response.md](./incident-response.md) - Core incident response protocol
- [../artifacts/receipt-schema.md](../artifacts/receipt-schema.md) - Receipt structure
- [../artifacts/handoff-protocol.md](../artifacts/handoff-protocol.md) - Envelope structure
- [../execution/resume-protocol.md](../execution/resume-protocol.md) - Resuming failed runs
- [../execution/detour-catalog.md](../execution/detour-catalog.md) - Known fix patterns
