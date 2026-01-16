# Git Safety

Shadow fork = full autonomy. Publish boundary = strict controls.

## Inside Shadow Fork (Flows 1-5)

All operations permitted:
- `git reset --hard` - OK
- `git push --force origin branch` - OK
- `git rebase` - OK
- Delete branches - OK

The fork is isolated. None of this affects upstream.

## At Publish Boundary (Flow 6)

Restricted:
- No force push to upstream
- No history rewriting on upstream
- Human approval for merge
- Secrets scan before push

## Rules

- Inside fork: work freely
- At boundary: gate strictly
- Flow 8 (Rebase) bridges deliberately
- Never force push to `upstream/*`
