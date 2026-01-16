# Incidents

Detect → Contain → Diagnose → Fix → Verify → Document

## Severity

| Sev | Description | Response |
|-----|-------------|----------|
| SEV1 | Production down, data loss, security breach | Immediate |
| SEV2 | Degraded service, blocked deploys | Same-day |
| SEV3 | Bug affecting users, failed runs | Next business day |
| SEV4 | Minor/cosmetic | Backlog |

## The Rule

- Contain immediately. Trust physics (logs, exit codes), not claims.
- When in doubt, escalate up.
- Post-mortem: SEV1 within 48h, SEV2 within 1 week
- Focus on systems, not people. Use 5 Whys.

## Failed Runs

Check receipt → status → error → transcript → handoff envelope. Check artifacts before asking the agent.

> Docs: docs/safety/INCIDENT_RESPONSE.md
