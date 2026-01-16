# Deprecation Migration

Every deprecation has a migration guide.

## Required Documentation
1. **Summary**: What's changing (1 paragraph)
2. **Timeline**: When each stage happens
3. **Migration steps**: Numbered, actionable
4. **Mapping table**: Old → New for all fields
5. **Edge cases**: Known issues and workarounds
6. **Rollback**: How to undo
7. **Support**: Where to get help

## Tooling Requirements
- Migration scripts should be idempotent (safe to run multiple times)
- Dry-run mode required
- Detailed logs produced

## Warning Integration
Warnings appear in:
- CLI output
- Log files
- Validation output (`make validate-swarm`)
- Documentation (deprecation badges)

## The Rule
- Tooling should be idempotent
- Warnings appear everywhere users interact
- Migration guide required before marking deprecated

> Skill: deprecation-migration
> Docs: docs/governance/DEPRECATION.md
