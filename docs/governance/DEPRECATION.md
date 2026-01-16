# Deprecation

Deprecation is a staged lifecycle. Silent removal is banned.

## Stages

1. **Deprecated**: Warnings + alternative named
2. **Migration**: Guide + tooling where feasible
3. **Disabled**: Still present; off by default
4. **Removed**: After minimum windows

## Timing

- ≥ 2 releases from migration → disabled
- ≥ 1 release from disabled → removed

## Migration Requirements

1. Summary (1 paragraph)
2. Timeline
3. Migration steps (numbered, actionable)
4. Mapping table (old → new)
5. Edge cases and workarounds
6. Rollback instructions
7. Support contact

## Tooling

- Migration scripts should be idempotent
- Dry-run mode required
- Detailed logs produced

## Rules

- Warnings appear everywhere users interact
- Migration guide required before marking deprecated
- Tooling should be idempotent
