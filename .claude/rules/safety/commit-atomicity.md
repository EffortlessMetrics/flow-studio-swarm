# Commit Atomicity

Commits must be atomic, traceable, and bisectable.

## One Logical Change Per Commit

| Commit | Content | Atomic? |
|--------|---------|---------|
| `feat: add user model` | Model + migration + tests | Yes (one feature) |
| `fix: auth + logging` | Two unrelated fixes | No (split them) |
| `refactor: extract utils` | Only the extraction | Yes (one refactor) |
| `chore: deps + config` | Dependencies + unrelated config | No (split them) |

```bash
# BAD: Kitchen sink commit
git commit -m "fix: auth bug, add logging, update deps, refactor utils"

# GOOD: Separate commits
git commit -m "fix: prevent null pointer in auth check"
git commit -m "feat: add structured logging to auth module"
git commit -m "chore: update cryptography to 42.0"
git commit -m "refactor: extract validation to separate module"
```

## Tests Must Pass at Each Commit

```bash
# Bisectable history means:
git checkout HEAD~5  # Tests should pass
git checkout HEAD~3  # Tests should pass
git checkout HEAD    # Tests should pass

# BAD pattern:
# commit 1: "feat: add feature (broken)"
# commit 2: "fix: make tests pass"

# GOOD pattern:
# commit 1: "feat: add feature" (tests pass)
```

## Why Bisectable History Matters

When debugging regressions:
```bash
git bisect start
git bisect bad HEAD
git bisect good v1.2.0
# Git binary searches to find the breaking commit
# Only works if each commit is valid
```

## What Commits Must NOT Contain

### Multiple Unrelated Changes

Split unrelated work into separate commits.

### Generated Files Without Source Changes

```bash
# BAD: Commit only the generated output
git add dist/bundle.js
git commit -m "chore: update bundle"

# GOOD: Commit source with generated files
git add src/app.ts dist/bundle.js
git commit -m "feat: add dashboard component"
```

### Secrets, Credentials, API Keys

```bash
# NEVER commit these:
API_KEY=sk-1234567890abcdef...
password: "hunter2"
aws_secret_access_key: AKIA...

# If committed accidentally:
# 1. Rotate the credential immediately
# 2. Use git filter-branch or BFG to remove from history
# 3. Force push (with approval at publish boundary)
```

### Large Binary Files

```bash
# BAD: Large binaries in repo
git add model.pkl  # 500MB

# GOOD: Use Git LFS or external storage
git lfs track "*.pkl"
git add .gitattributes
```

## The Rule

> One logical change per commit. Tests pass at every commit.
> Never commit secrets. Never commit binaries without LFS.

---

## See Also
- [commit-message-format.md](./commit-message-format.md) - Message format and types
- [commit-agent-generated.md](./commit-agent-generated.md) - Agent commit requirements
- [secret-management.md](./secret-management.md) - Secret handling
