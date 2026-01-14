# Dependency Patterns: What to Avoid and Prefer

## Purpose

Catalog of banned and preferred dependency patterns. Know what to avoid, what to prefer, and when to remove.

## The Rule

> Prefer stdlib. Prefer existing deps. Prefer copy-paste.
> When you must add one: maintain it like your own code.

## Banned Patterns

### Deps for Trivial Functions

**The left-pad rule:** If you can write it in < 20 lines and it won't change, don't import it.

```javascript
// BAD: Adding a dep for this
import leftPad from 'left-pad';

// GOOD: Just write it
const leftPad = (str, len, ch = ' ') =>
  str.padStart(len, ch);
```

### Unmaintained Dependencies

No commits in 2+ years = abandoned. Exceptions require:
- Explicit acknowledgment of risk
- Plan for maintenance if upstream dies
- Fork readiness

### Known Unpatched Vulnerabilities

Zero tolerance for HIGH/CRITICAL unpatched CVEs in runtime deps.

Dev deps: case-by-case, but document the risk.

### Massive Transitive Trees

If a utility pulls 100+ transitive deps, the cost exceeds the benefit. Find an alternative or write it yourself.

## Preferred Patterns

### Stdlib Over External

```python
# PREFERRED: stdlib
import json
from pathlib import Path
from dataclasses import dataclass

# AVOID: external for stdlib-equivalent
import simplejson  # json works fine
import pathlib2    # use stdlib pathlib
import attrs       # dataclasses exist
```

### Focused Deps Over Frameworks

```javascript
// PREFERRED: focused utility
import slugify from 'slugify';  // Does one thing

// AVOID: kitchen sink
import lodash from 'lodash';    // 99% unused
```

If you need 2-3 lodash functions, import them individually or copy them.

### Pinned Versions Over Ranges

```json
// PREFERRED: exact versions
"dependencies": {
  "express": "4.18.2"
}

// RISKY: ranges
"dependencies": {
  "express": "^4.18.2"
}
```

Ranges invite surprise breakage. Pin versions, update deliberately.

### Lock Files Committed

Always commit:
- `package-lock.json` (npm)
- `uv.lock` / `poetry.lock` (Python)
- `go.sum` (Go)

Lock files ensure reproducible builds. Never gitignore them.

## When to Remove Dependencies

### No Longer Used

Dead code detection should include dead deps. If nothing imports it, remove it.

```bash
# Check for unused deps
npx depcheck
pip-extra-reqs .
```

### Better Alternative Exists

When stdlib catches up or a better-maintained option emerges, migrate.

Example: `moment.js` → `date-fns` or native `Intl`

### Security Concerns

Unpatched vulnerabilities with no fix timeline = remove or fork.

### Maintenance Abandoned

Upstream stopped responding to issues/PRs = assess risk, plan exit.

## The Economics

| Cost | Description |
|------|-------------|
| **Install time** | Every CI run, every dev setup |
| **Update burden** | Security patches, breaking changes |
| **Debug surface** | More code = more places bugs hide |
| **Supply chain risk** | Compromised upstream = compromised you |
| **Cognitive load** | Another API to learn, another changelog to read |

Benefits must exceed these costs. For trivial utilities, they rarely do.

---

## See Also

- [dependency-intake.md](./dependency-intake.md) - The five questions before adding a dependency
- [git-safety.md](./git-safety.md) - Safe operations for dependency updates
- [boundary-automation.md](./boundary-automation.md) - Supply chain at publish boundary
