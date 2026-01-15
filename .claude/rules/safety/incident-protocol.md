# Incident Protocol

The 6-step process for handling incidents consistently.

## The Six Steps

### 1. Detect

How was the incident discovered?

| Detection Source | Action |
|------------------|--------|
| Monitoring alert | Acknowledge alert, check dashboard |
| User report | Confirm reproduction, gather details |
| Failed run | Check receipts, identify failing step |
| Audit discovery | Document finding, assess scope |
| Routine check | Escalate based on severity |

**Capture immediately:**
- Timestamp of discovery
- Who/what detected it
- Initial symptoms observed

### 2. Contain

Stop the bleeding. Prioritize containment over diagnosis.

| Incident Type | Containment Action |
|---------------|-------------------|
| Security breach | Revoke credentials, isolate affected systems |
| Production down | Revert to last known good, enable maintenance mode |
| Blocked deployments | Pause pipeline, notify stakeholders |
| Failed runs | Mark run as failed, prevent downstream effects |
| Data corruption | Stop writes, snapshot current state |

**Containment checklist:**
- [ ] Immediate harm stopped
- [ ] Scope of impact identified
- [ ] Stakeholders notified (SEV1/SEV2)
- [ ] Containment action documented

### 3. Diagnose

What went wrong? Follow the evidence.

**Evidence sources (priority order):**
1. **Physics**: Exit codes, file states, git status
2. **Receipts**: Step receipts, command outputs, logs
3. **Artifacts**: Generated files, diffs, handoff envelopes
4. **Narrative**: Agent claims, user reports

**Diagnosis steps:**
1. Identify the failing component (flow, step, agent)
2. Check the evidence trail (receipts, status, freshness)
3. Reproduce if possible (same inputs → same failure?)
4. Trace backward (last successful state?)
5. Identify root cause (not just proximate cause)

### 4. Fix

Implement the solution. Prefer reversible fixes.

| Fix Type | When to Use |
|----------|-------------|
| **Revert** | Known-good state exists, low risk |
| **Hotfix** | Small, targeted fix, urgent |
| **Full fix** | Root cause addressed, time available |
| **Workaround** | Temporary mitigation, buy time |

**Fix requirements:**
- [ ] Fix addresses root cause (or documents why not)
- [ ] Fix is tested before deployment
- [ ] Rollback plan exists
- [ ] Change is documented

### 5. Verify

Confirm the fix works. Trust physics, not narrative.

**Verification checklist:**
- [ ] Original failure no longer reproduces
- [ ] Related functionality still works
- [ ] Evidence shows fix is effective
- [ ] No new issues introduced

### 6. Document

Create the post-mortem. This is mandatory for SEV1/SEV2.

See [incident-postmortem.md](./incident-postmortem.md) for requirements.

## Incident Capture Template

During the incident, capture:

```markdown
## Incident Timeline

| Time | Event | Evidence |
|------|-------|----------|
| HH:MM | Incident detected | <how> |
| HH:MM | Containment started | <action> |
| HH:MM | Root cause identified | <finding> |
| HH:MM | Fix deployed | <change> |
| HH:MM | Verification complete | <evidence> |

## Commands Run

(Include actual commands and their output)

## Decisions Made

| Decision | Rationale | Alternative Considered |
|----------|-----------|------------------------|
| ... | ... | ... |

## Who Was Involved

| Role | Person | Contribution |
|------|--------|--------------|
| Incident Commander | ... | ... |
| Technical Lead | ... | ... |
```

## The Rule

> Detect fast. Contain immediately. Diagnose thoroughly.
> Fix with evidence. Verify with physics. Document for learning.

---

## See Also
- [incident-severity.md](./incident-severity.md) - Severity levels and classification
- [incident-postmortem.md](./incident-postmortem.md) - Post-mortem requirements
- [rollback-types.md](./rollback-types.md) - Rollback methods
- [../governance/evidence-discipline.md](../governance/evidence-discipline.md) - Evidence requirements
