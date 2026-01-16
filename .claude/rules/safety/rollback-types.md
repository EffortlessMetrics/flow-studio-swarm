# Rollback Types

When something breaks, choose the right rollback method.

## Methods
| Type | When | Where |
|------|------|-------|
| **Git Revert** | Undo on upstream | Creates new commit, preserves history |
| **Git Reset** | Shadow fork only | Rewrites history, NEVER on upstream |
| **Feature Disable** | Fastest response | Runtime flag, code stays deployed |
| **Data Rollback** | Corruption | Restore from backup, reconcile carefully |

## Decision
- Production broken + can disable via flag → Feature Disable
- Production broken + no flag → Git Revert
- Shadow fork issue → Git Reset
- Data corruption → Data Rollback (last resort)

## The Rule
- Prefer reversible actions
- Revert first, investigate second
- Git Reset = shadow fork ONLY, never upstream

> Docs: docs/safety/ROLLBACK_GUIDE.md
