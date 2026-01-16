---
name: dependency-review
description: Review new dependencies for security and maintenance risk. Use when adding or updating dependencies.
---
# Dependency Review

1. Justify need: Can stdlib or existing deps solve this?
2. Check maintenance: Commits < 6 months, responsive maintainers?
3. Check security: No unpatched HIGH/CRITICAL CVEs?
4. Check size: Reasonable transitive dependency count?
5. Check license: Compatible with project?
6. Document rationale in PR with risk assessment.
