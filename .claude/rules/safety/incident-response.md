# Incident Response Protocol

**"When things go wrong, fix forward with evidence."**

Incidents are inevitable. This protocol ensures they are handled consistently, documented thoroughly, and learned from systematically.

## Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **SEV1** | Production down, data loss, security breach | Immediate | Secrets leaked, upstream corrupted, service outage |
| **SEV2** | Degraded service, blocked deployments | Same-day | CI pipeline broken, deploys failing, major feature broken |
| **SEV3** | Bug affecting users, failed runs | Next business day | Flow failures, incorrect outputs, flaky tests |
| **SEV4** | Minor issue, cosmetic | Normal backlog | Typos, minor UI issues, non-blocking warnings |

### Severity Decision Tree

```
Is production affected?
├── Yes → Is data lost or security compromised?
│         ├── Yes → SEV1
│         └── No → SEV2
└── No → Are users blocked?
          ├── Yes → SEV2
          └── No → Is it affecting correctness?
                    ├── Yes → SEV3
                    └── No → SEV4
```

## Response Protocol

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
```
1. Identify the failing component
   └── Which flow? Which step? Which agent?

2. Check the evidence trail
   └── Receipt exists? Status? Evidence fresh?

3. Reproduce if possible
   └── Same inputs → same failure?

4. Trace backward
   └── What was the last successful state?

5. Identify root cause
   └── Not just proximate cause
```

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

```bash
# Include actual commands and their output
command_1
# output...

command_2
# output...
```

## Decisions Made

| Decision | Rationale | Alternative Considered |
|----------|-----------|------------------------|
| ... | ... | ... |

## Who Was Involved

| Role | Person | Contribution |
|------|--------|--------------|
| Incident Commander | ... | ... |
| Technical Lead | ... | ... |
| ... | ... | ... |
```

## Post-Mortem Requirements

### Mandatory Elements

1. **Summary**: One paragraph describing what happened
2. **Impact**: Who was affected, for how long, what was the scope
3. **Timeline**: Chronological events with timestamps
4. **Root Cause**: Not proximate cause, but underlying issue
5. **Contributing Factors**: What made this possible
6. **Action Items**: Specific, owned, with deadlines
7. **Prevention Measures**: How to prevent recurrence

### The Blameless Rule

> Focus on systems, not people.
> "The deploy script failed" not "John broke the deploy"
> "The validation didn't catch this" not "Nobody reviewed properly"

**Questions to ask:**
- What system allowed this to happen?
- What signal was missed?
- What would have prevented this?
- What would have detected this earlier?

**Questions to avoid:**
- Who made the mistake?
- Why didn't someone catch this?
- Whose fault is this?

### Root Cause Analysis

Find the root cause, not just the proximate cause.

| Level | Example |
|-------|---------|
| **Symptom** | Tests failed in CI |
| **Proximate cause** | Test file was missing import |
| **Contributing factor** | No import validation in pre-commit |
| **Root cause** | New dependency added without updating test fixtures |
| **Systemic issue** | Dependency changes don't trigger test fixture review |

Use the "5 Whys" technique:
1. Why did tests fail? → Missing import
2. Why was import missing? → New dependency not in test requirements
3. Why wasn't it in test requirements? → Added to main but not test
4. Why wasn't this caught? → No pre-commit check for import consistency
5. Why no pre-commit check? → Import validation not part of standard checks

**Root cause:** Import validation missing from pre-commit hooks.

## The Rule

> Detect fast. Contain immediately. Diagnose thoroughly.
> Fix with evidence. Verify with physics. Document for learning.
> Blame systems, not people. Prevent recurrence, not just repeat.

---

## See Also
- [incident-response-flowstudio.md](./incident-response-flowstudio.md) - Flow Studio specific incident playbooks
- [boundary-automation.md](./boundary-automation.md) - Publish gate enforcement
- [git-safety.md](./git-safety.md) - Git operations safety
- [sandbox-and-permissions.md](./sandbox-and-permissions.md) - Containment model
- [../governance/evidence-discipline.md](../governance/evidence-discipline.md) - Evidence requirements
- [../governance/truth-hierarchy.md](../governance/truth-hierarchy.md) - Evidence levels
