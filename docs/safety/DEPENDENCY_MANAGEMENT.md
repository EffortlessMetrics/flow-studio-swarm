# Dependency Management

Every dependency is a liability. Justify its existence.

## Five Questions

1. Is this solving a problem we actually have NOW?
2. Can we solve it with stdlib or existing deps?
3. Is the dependency maintained? (commits < 6mo)
4. Security posture? (no unpatched HIGH/CRITICAL CVEs)
5. Size impact? (< 10 new transitive deps for utilities)

If any answer is "no" or "unknown", stop and reconsider.

## Banned

- Deps for trivial functions (< 20 lines)
- Unmaintained (no commits 2+ years)
- Known unpatched vulnerabilities
- Massive transitive trees

## Preferred

- Stdlib over external
- Focused deps over frameworks
- Pinned versions over ranges
- Lock files always committed

## When to Remove

- No longer used
- Better alternative exists
- Security concerns with no fix timeline
- Maintenance abandoned
