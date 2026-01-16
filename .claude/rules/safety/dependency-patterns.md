# Dependency Patterns

Prefer stdlib. When you must add one, maintain it like your own code.

## Banned
- Deps for trivial functions (< 20 lines, won't change)
- Unmaintained (no commits 2+ years)
- Known unpatched vulnerabilities (HIGH/CRITICAL)
- Massive transitive trees (100+ deps for a utility)

## Preferred
- Stdlib over external
- Focused deps over frameworks
- Pinned versions over ranges
- Lock files always committed

## When to Remove
- No longer used (dead code detection)
- Better alternative exists
- Security concerns with no fix timeline
- Maintenance abandoned

## The Rule
- If you can write it in < 20 lines, don't import it
- Pin versions, update deliberately
- Benefits must exceed: install time + update burden + debug surface + supply chain risk

> Docs: docs/safety/DEPENDENCY_MANAGEMENT.md
