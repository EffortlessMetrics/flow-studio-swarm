# Rollbacks

Design for rollback from the start. Prefer reversible actions.

## Methods

| Type | When | Constraint |
|------|------|------------|
| Feature Disable | Fastest response | Flag must exist |
| Git Revert | Undo on upstream | Creates new commit |
| Git Reset | Shadow fork only | NEVER on upstream |
| Data Rollback | Corruption | Last resort |

## Prevention

- Staged rollouts with monitoring between stages
- Feature flags for new functionality
- Backward-compatible migrations (expand-contract)

## The Rule

- Revert first, investigate second
- Git Reset = shadow fork ONLY, never upstream
- Build with the assumption rollback will be needed
- Deploy incrementally to limit blast radius

> Docs: docs/safety/ROLLBACK_GUIDE.md
