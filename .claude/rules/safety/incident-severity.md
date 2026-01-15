# Incident Severity

How to classify and prioritize incidents by severity.

## Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **SEV1** | Production down, data loss, security breach | Immediate | Secrets leaked, upstream corrupted, service outage |
| **SEV2** | Degraded service, blocked deployments | Same-day | CI pipeline broken, deploys failing, major feature broken |
| **SEV3** | Bug affecting users, failed runs | Next business day | Flow failures, incorrect outputs, flaky tests |
| **SEV4** | Minor issue, cosmetic | Normal backlog | Typos, minor UI issues, non-blocking warnings |

## Severity Decision Tree

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

## Response Time Expectations

| Severity | Initial Response | Resolution Target |
|----------|------------------|-------------------|
| SEV1 | Immediate | ASAP, all hands |
| SEV2 | Within hours | Same day |
| SEV3 | Next business day | Within sprint |
| SEV4 | Normal triage | Backlog prioritization |

## The Rule

> Classify immediately. Response time follows severity.
> When in doubt, escalate up (SEV3 → SEV2).

---

## See Also
- [incident-protocol.md](./incident-protocol.md) - The 6-step response protocol
- [incident-postmortem.md](./incident-postmortem.md) - Post-mortem requirements
- [incident-failed-run.md](./incident-failed-run.md) - Failed run playbook
- [incident-stuck-wrong.md](./incident-stuck-wrong.md) - Stuck runs and wrong output playbooks
