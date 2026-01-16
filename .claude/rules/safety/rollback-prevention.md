# Rollback Prevention

Design for rollback from the start.

## Strategies
- **Staged rollouts**: 1% → 5% → 25% → 100%, with monitoring between
- **Canary deployments**: New version alongside old, traffic splitting
- **Feature flags**: Wrap risky code for instant disable
- **Backward-compatible migrations**: Old code works with new schema

## Pre-Deploy Checklist
- [ ] Revert commit identified
- [ ] Feature flag exists (for new functionality)
- [ ] DB migrations are backward-compatible
- [ ] Monitoring alerts configured
- [ ] Rollback tested in staging

## The Rule
- Deploy incrementally to limit blast radius
- Never deploy breaking migrations without expand-contract pattern
- Build with the assumption rollback will be needed

> Docs: docs/safety/ROLLBACK_GUIDE.md
