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

1. Failure detected
2. Signature matched? → Route to detour
3. Detour executes fix
4. Verify fix
5. Return to main path

## Limits

- Default: 2 attempts per detour type per step
- After limit: Escalate or advance with warnings

## Rules

- Match signatures to detours before generic iteration
- Detours are cheap; re-discovery is expensive
- If detour fails twice, escalate
