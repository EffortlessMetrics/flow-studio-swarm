---
paths:
  - "**/*.md"
  - "**/*.py"
  - "**/*.ts"
  - "**/*.js"
---

# Git Safety Rules

These rules apply when agents perform git operations.

## Prohibited Operations

NEVER execute:
- `git push --force` or `git push -f`
- `git reset --hard` (without explicit human approval)
- `git clean -fd` (without explicit human approval)
- `git rebase -i` (interactive mode not supported)
- `git stash drop` without explicit naming

## Safe Patterns

### Commits
- Always use conventional commit format
- Never commit secrets or credentials
- Use `--no-verify` only when explicitly instructed
- Prefer small, atomic commits

### Branches
- Create feature branches for new work: `feature/*`, `fix/*`, `chore/*`
- Never delete protected branches: `main`, `master`, `develop`, `release/*`
- Always check branch before destructive operations

### Resets
- Prefer `git reset --soft` or `git reset --mixed`
- If `--hard` needed, stash first: `git stash push -m "before-reset"`
- Log the reset reason in commit message

### Conflict Resolution
- Never force-resolve conflicts
- Escalate complex conflicts to human review
- Document resolution strategy in commit message

## Protected Branches

| Branch Pattern | Delete | Force Push | Direct Commit |
|----------------|--------|------------|---------------|
| `main`, `master` | NEVER | NEVER | NEVER |
| `develop` | NEVER | NEVER | ASK |
| `release/*` | NEVER | NEVER | NEVER |
| `hotfix/*` | NEVER | NEVER | ASK |
| `feature/*` | OK | ASK | OK |

## Conflict Resolution Ladder

1. **Auto-merge**: Simple conflicts (whitespace, imports) → auto-resolve
2. **Structured merge**: Code conflicts → attempt structured resolution
3. **Human escalate**: Semantic conflicts → document and escalate

## Enforcement

- `repo-operator` agent uses safe Bash commands only
- `.claude/settings.json` has `askBefore` rules for dangerous commands
- Boundary agents validate git state before publishing
