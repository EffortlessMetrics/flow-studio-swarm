# Commit Message Format

How to write commit messages that serve as audit artifacts.

## Subject Line

```
<type>: <description>
```

- **50 character limit** for subject line
- **Lowercase** after the colon
- **No period** at the end
- **Imperative mood**: "add feature" not "added feature"

## Types

| Type | Purpose | Example |
|------|---------|---------|
| `feat` | New feature or capability | `feat: add OAuth2 login flow` |
| `fix` | Bug fix | `fix: prevent null pointer in auth check` |
| `refactor` | Code change that neither fixes nor adds | `refactor: extract validation logic` |
| `docs` | Documentation only | `docs: update API reference` |
| `test` | Adding or fixing tests | `test: add edge cases for token refresh` |
| `chore` | Maintenance, deps, tooling | `chore: upgrade pytest to 8.0` |

## Body

The body explains **what** and **why**, not **how**.

```
feat: add rate limiting to API endpoints

Rate limiting prevents abuse and ensures fair resource allocation.
Current implementation uses token bucket algorithm with 100 req/min
per authenticated user.

Fixes #234
```

**Good body content:**
- Why this change is necessary
- What problem it solves
- What alternative approaches were considered
- Any non-obvious implications

**Bad body content:**
- Line-by-line code explanation
- Implementation details visible in diff
- "Updated file X" (obvious from diff)

## Issue References

| Syntax | Meaning | When to Use |
|--------|---------|-------------|
| `Fixes #123` | Closes issue on merge | Bug fixes, feature completion |
| `Closes #123` | Closes issue on merge | Same as Fixes |
| `Relates to #456` | Links without closing | Partial work, related context |
| `Part of #789` | Work toward larger issue | Incremental progress |

## Examples: Good vs Bad

```bash
# BAD: Vague
git commit -m "fix stuff"

# BAD: Too long subject
git commit -m "fix: this commit fixes the bug where users couldn't log in"

# BAD: Past tense
git commit -m "fix: fixed the login bug"

# BAD: No type
git commit -m "add rate limiting"

# GOOD: Clear, typed, imperative
git commit -m "fix: prevent session timeout during active use"
```

## The Rule

> Subject: <type>: <description> (50 chars, imperative mood)
> Body: What and why, not how. Reference issues.

---

## See Also
- [commit-atomicity.md](./commit-atomicity.md) - Atomic and bisectable commits
- [commit-agent-generated.md](./commit-agent-generated.md) - Agent commit requirements
- [git-safety.md](./git-safety.md) - Git operations by zone
