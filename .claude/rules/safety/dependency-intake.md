# Dependency Intake: The Five Questions

## Purpose

Before adding any dependency, pass the intake checklist. Dependencies are liabilities that require justification.

## The Rule

> Every dependency is a liability. Justify its existence.
> Ask five questions in order. If any answer is "no" or "unknown," stop and reconsider.

## The Five Questions

### 1. Is this solving a problem we actually have?

Not a problem we might have. Not a problem that sounds interesting. A problem we have **right now** that is blocking work.

**Red flags:**
- "We might need this later"
- "It's best practice"
- "Everyone uses it"

**Green flags:**
- "We tried without it and hit [specific blocker]"
- "The alternative is 200+ lines of error-prone code"

### 2. Can we solve it with existing deps or stdlib?

Check in this order:
1. **Standard library** - Python stdlib, Node built-ins, Go stdlib
2. **Existing dependencies** - Something already in the tree
3. **Copy-paste** - Small, stable code that won't change

Only after exhausting these: consider a new dependency.

### 3. Is the dependency maintained?

| Signal | Healthy | Concerning | Abandon |
|--------|---------|------------|---------|
| Last commit | < 6 months | 6-18 months | > 2 years |
| Open issues | Triaged, responded | Backlog growing | Ignored |
| Bus factor | 3+ maintainers | 1-2 maintainers | Solo + inactive |
| Release cadence | Regular | Sporadic | Stalled |

**Check:** GitHub/GitLab activity, npm/PyPI download trends, issue response time.

### 4. What's the security posture?

| Check | How | Acceptable |
|-------|-----|------------|
| Known vulns | `npm audit`, `pip-audit`, Snyk, Dependabot | Zero HIGH/CRITICAL unpatched |
| Audit history | Security advisories, CVE history | Responsive to past issues |
| Permissions | What does it access? | Minimal scope |
| Supply chain | Who owns it? Org vs individual? | Verifiable ownership |

**Blockers:**
- Known unpatched vulnerabilities (HIGH or CRITICAL)
- History of slow security response
- Unclear ownership or transfer history

### 5. What's the size impact?

| Metric | Check | Threshold |
|--------|-------|-----------|
| Direct size | Package size | Proportional to value |
| Transitive deps | `npm ls`, `pipdeptree` | < 10 new transitive deps |
| Bundle impact | Build before/after | < 5% increase for non-core |

**Red flags:**
- 50+ transitive dependencies for a utility function
- Pulls in framework-scale deps for small features
- Bundles native binaries unnecessarily

## Approval Requirements

### New Runtime Dependency

**Bar: HIGH** - These ship to production.

Required in PR:
- [ ] Answers to all five questions above
- [ ] Alternative approaches considered
- [ ] Size/security audit results
- [ ] Explicit reviewer approval

### New Dev Dependency

**Bar: MEDIUM** - These affect the build, not production.

Required in PR:
- [ ] Problem statement
- [ ] Why existing tools don't suffice
- [ ] Brief maintenance check

### Version Bumps

**Bar: VARIABLE** - Depends on change scope.

| Bump Type | Requirement |
|-----------|-------------|
| Patch (x.x.PATCH) | Changelog glance, CI green |
| Minor (x.MINOR.x) | Changelog review, test coverage |
| Major (MAJOR.x.x) | Breaking changes documented, migration tested |

## Enforcement

Dependency changes are reviewed for:
- Justification present in PR
- Five questions answered
- No banned patterns (see `dependency-patterns.md`)
- Lock file updated

Automated checks:
- `npm audit` / `pip-audit` in CI
- Dependabot / Renovate for updates
- Bundle size tracking (if applicable)

---

## See Also

- [dependency-patterns.md](./dependency-patterns.md) - Banned and preferred patterns, when to remove
- [git-safety.md](./git-safety.md) - Safe operations for dependency updates
- [boundary-automation.md](./boundary-automation.md) - Supply chain at publish boundary
