# Detour Catalog

Known problems deserve known solutions.

## Standard Detours
| Signature | Target | Resolution |
|-----------|--------|------------|
| `lint_errors` | auto-linter | Apply fixes, verify clean |
| `missing_import` | import-fixer | Add imports, verify passes |
| `type_mismatch` | type-annotator | Fix annotations, verify mypy |
| `test_fixture_missing` | test-setup | Create fixtures, verify tests |
| `upstream_diverged` | Flow 8 (Reset) | Fetch, rebase, resolve |

## Detour Flow

Failure → match signature → route to detour → verify fix → return to main path.

## Limits
- Default: 2 attempts per detour type per step
- After limit: Escalate or advance with warnings

## The Rule
- Match signatures to detours before generic iteration
- Detours are cheap; re-discovery is expensive
- If detour fails twice, escalate

> Docs: docs/execution/DETOUR_CATALOG.md
