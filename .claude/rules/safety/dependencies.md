# Dependencies

Every dependency is a liability. Justify its existence.

## Intake Questions

1. Problem we have NOW?
2. Solvable with stdlib or existing deps?
3. Maintained? (commits < 6mo, responsive maintainers)
4. Secure? (no unpatched HIGH/CRITICAL CVEs)
5. Size impact? (< 10 new transitive deps for utilities)

If any answer is "no" or "unknown", stop.

## Banned

- Trivial functions (< 20 lines, won't change)
- Unmaintained (no commits 2+ years)
- Known unpatched vulnerabilities
- Massive transitive trees (100+ deps for a utility)

## The Rule

- Prefer: stdlib > existing deps > copy-paste > new dep
- Pin versions, commit lock files
- Every new dep needs justification in PR
- If you can write it in < 20 lines, don't import it

> Docs: docs/safety/DEPENDENCY_MANAGEMENT.md
