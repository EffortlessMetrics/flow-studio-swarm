# Incident Response

Detect → Contain → Diagnose → Fix → Verify → Document

## Severity Levels

| Sev | Description | Response |
|-----|-------------|----------|
| SEV1 | Production down, data loss, security breach | Immediate |
| SEV2 | Degraded service, blocked deploys | Same-day |
| SEV3 | Bug affecting users, failed runs | Next business day |
| SEV4 | Minor/cosmetic | Backlog |

When in doubt, escalate up.

## Containment Priority

- Security breach → revoke credentials, isolate
- Production down → revert to last known good
- Failed runs → mark failed, prevent downstream

## Post-Mortem (Required for SEV1-2)

1. Summary (one paragraph)
2. Impact (scope, duration)
3. Timeline (chronological)
4. Root cause (not proximate)
5. Action items (owned, deadlines)

Focus on systems, not people. Use the 5 Whys.

## Rules

- Contain immediately
- Trust physics (logs, exit codes), not claims
- SEV1 post-mortem within 48 hours
