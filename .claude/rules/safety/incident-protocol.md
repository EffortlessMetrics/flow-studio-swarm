# Incident Protocol

Detect → Contain → Diagnose → Fix → Verify → Document

## Containment Priority
- Security breach → revoke credentials, isolate
- Production down → revert to last known good
- Failed runs → mark failed, prevent downstream

## The Rule
Contain immediately. Trust physics (logs, exit codes), not claims.

> Docs: docs/safety/INCIDENT_RESPONSE.md
