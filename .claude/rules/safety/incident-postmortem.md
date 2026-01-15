# Incident Post-Mortem

Requirements for post-incident documentation and learning.

## Mandatory Elements

1. **Summary**: One paragraph describing what happened
2. **Impact**: Who was affected, for how long, what was the scope
3. **Timeline**: Chronological events with timestamps
4. **Root Cause**: Not proximate cause, but underlying issue
5. **Contributing Factors**: What made this possible
6. **Action Items**: Specific, owned, with deadlines
7. **Prevention Measures**: How to prevent recurrence

## The Blameless Rule

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

## Root Cause Analysis

Find the root cause, not just the proximate cause.

| Level | Example |
|-------|---------|
| **Symptom** | Tests failed in CI |
| **Proximate cause** | Test file was missing import |
| **Contributing factor** | No import validation in pre-commit |
| **Root cause** | New dependency added without updating test fixtures |
| **Systemic issue** | Dependency changes don't trigger test fixture review |

### The 5 Whys Technique

1. Why did tests fail? → Missing import
2. Why was import missing? → New dependency not in test requirements
3. Why wasn't it in test requirements? → Added to main but not test
4. Why wasn't this caught? → No pre-commit check for import consistency
5. Why no pre-commit check? → Import validation not part of standard checks

**Root cause:** Import validation missing from pre-commit hooks.

## When Post-Mortems Are Required

| Severity | Post-Mortem Required | Timing |
|----------|---------------------|--------|
| SEV1 | Mandatory | Within 48 hours |
| SEV2 | Mandatory | Within 1 week |
| SEV3 | Recommended | Within sprint |
| SEV4 | Optional | As time permits |

## The Rule

> Blame systems, not people. Find root cause, not proximate cause.
> Document for learning, not punishment. Prevent recurrence.

---

## See Also
- [incident-severity.md](./incident-severity.md) - Severity levels and classification
- [incident-protocol.md](./incident-protocol.md) - The 6-step response protocol
- [../governance/calibration-loop.md](../governance/calibration-loop.md) - Learning feedback system
