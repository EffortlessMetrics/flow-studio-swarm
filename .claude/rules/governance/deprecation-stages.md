# Deprecation Stages

Deprecation is a staged lifecycle. Silent removal is banned.

## The Rule
Stages:
1. **Deprecated** (warnings + alternative named)
2. **Migration** (guide + tooling where feasible)
3. **Disabled** (still present; off by default)
4. **Removed** (after minimum windows)

Timing:
- ≥ 2 releases from migration → disabled
- ≥ 1 release from disabled → removed

> Skill: deprecation-migration
> Docs: docs/governance/DEPRECATION.md
