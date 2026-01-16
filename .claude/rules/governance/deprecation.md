# Deprecation

Silent removal is banned. Breaking changes require migration.

## Lifecycle Stages

1. **Deprecated** (warnings + alternative named)
2. **Migration** (guide + tooling where feasible)
3. **Disabled** (still present; off by default)
4. **Removed** (after minimum windows: ≥2 releases → disabled, ≥1 release → removed)

## Breaking Changes

Public contracts (schemas, CLI, APIs), stored data formats, external integrations.

## The Rule

- Migration guide required before marking deprecated
- Migration tooling is idempotent with dry-run
- Backward-compat changes bump minor. Breaking changes bump major.
- Rollback exists for destructive steps

> Docs: docs/governance/DEPRECATION.md
