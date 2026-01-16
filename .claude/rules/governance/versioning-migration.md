# Versioning Migration

Migrations must be executable and reversible.

## The Rule
- Migration steps are numbered and testable
- Tooling (if any) is **idempotent** and supports **dry-run**
- Logs are captured to evidence paths
- Rollback exists for destructive steps

If tooling cannot be provided: document manual steps and set risk explicitly.

> Skill: deprecation-migration
> Docs: docs/governance/MIGRATIONS.md
