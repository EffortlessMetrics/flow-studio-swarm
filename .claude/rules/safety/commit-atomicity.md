# Commit Atomicity

One logical change per commit. Tests pass at each commit.

## Atomic
- feat: add user model (model + migration + tests) ✓
- fix: auth + logging (two unrelated fixes) ✗ → split

## Never Commit
- Multiple unrelated changes
- Generated files without source
- Secrets, credentials, API keys
- Large binaries (use LFS)

## Bisectable History
Every commit must be valid for `git bisect`.

> Docs: docs/safety/COMMIT_GUIDELINES.md
