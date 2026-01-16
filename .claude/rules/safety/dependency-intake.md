# Dependency Intake

Every dependency is a liability. Justify its existence.

## Five Questions (in order)
1. Is this solving a problem we actually have NOW?
2. Can we solve it with stdlib or existing deps?
3. Is the dependency maintained? (commits < 6mo, responsive maintainers)
4. Security posture? (no unpatched HIGH/CRITICAL CVEs)
5. Size impact? (< 10 new transitive deps for utilities)

If any answer is "no" or "unknown", stop and reconsider.

## Approval Bar
- Runtime dep: HIGH (ships to production) - all 5 questions answered
- Dev dep: MEDIUM - problem statement + maintenance check
- Version bump: VARIABLE - changelog review proportional to change

## The Rule
- Prefer stdlib → existing deps → copy-paste → new dep
- Pin versions, commit lock files
- Every new dep needs justification in PR

> Docs: docs/safety/DEPENDENCY_MANAGEMENT.md
