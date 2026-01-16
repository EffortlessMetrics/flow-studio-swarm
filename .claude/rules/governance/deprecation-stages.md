# Deprecation Stages

External dependents get warning. Internal cleanup is encouraged.

## The Four Stages
1. **Marked**: Flagged, fully functional, warnings on use
2. **Migration**: Alternative documented, migration path clear
3. **Disabled**: Use triggers error, code remains (rollback possible)
4. **Removed**: Code deleted

## Timeline Requirements
| Transition | Minimum |
|------------|---------|
| Marked → Migration | Immediate (same release) |
| Migration → Disabled | 2 releases |
| Disabled → Removed | 1 release |

## What Requires Deprecation
- Agents, flows, artifact schemas, public APIs

## What Can Be Removed Directly
- Internal implementation details (not exposed)
- Unused code with no references
- Failed experiments (never shipped)

## The Rule
- Two releases minimum from migration to disabled
- One release from disabled to removed
- If external dependents exist, follow the process

> Docs: docs/governance/DEPRECATION.md
