# Incident Protocol

Six steps: Detect → Contain → Diagnose → Fix → Verify → Document.

## Steps
1. **Detect**: Acknowledge the incident, capture timestamp
2. **Contain**: Stop the bleeding first, prioritize over diagnosis
3. **Diagnose**: Follow evidence (physics > receipts > artifacts > narrative)
4. **Fix**: Prefer reversible fixes, have rollback plan
5. **Verify**: Confirm fix with evidence, not narrative
6. **Document**: Post-mortem for SEV1/SEV2

## Containment Priority
- Security breach → revoke credentials, isolate systems
- Production down → revert to last known good
- Failed runs → mark failed, prevent downstream effects

## The Rule
- Contain immediately, diagnose thoroughly
- Trust physics (exit codes, logs), not claims
- Document for learning, not punishment

> Skill: incident-response
> Docs: docs/safety/INCIDENT_RESPONSE.md
