# Sandbox

Autonomy requires isolation. Full freedom inside, strict gates at boundary.

## Inside Shadow Fork (Flows 1-5)

All operations permitted:
- `git reset --hard`, `git rebase`, `git push --force origin branch`
- Delete branches, rewrite history
- This is an isolated sandbox. None affects upstream.

## At Publish Boundary (Flow 6)

Restricted:
- Secrets scanning before push → BLOCK on detection
- Evidence exists and fresh → required
- No force push to upstream
- Human approval for merge

## bypassPermissions OK When

- Dedicated working directory (not home)
- No credentials in environment
- Git remotes controlled
- Publishing goes through boundary agents

## The Rule

- Inside fork: default-allow, work freely
- At boundary: fail-closed, gate strictly
- Flow 8 bridges upstream deliberately
- Never force push to `upstream/*`

> Docs: docs/safety/SANDBOX.md
