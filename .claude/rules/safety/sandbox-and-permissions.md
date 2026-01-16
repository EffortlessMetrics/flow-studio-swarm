# Sandbox and Permissions

Autonomy requires isolation.

## The Model
- **Inside sandbox**: Full autonomy, default-allow
- **At publish boundary**: Strict gates, fail-closed

## bypassPermissions is OK When
- [ ] Dedicated working directory (not home)
- [ ] No credentials in environment
- [ ] Git remotes controlled
- [ ] Publishing goes through boundary agents

## Boundary Blocks
- `git push --force` → BLOCKED
- `.env*`, `secrets/**`, `~/.ssh/**` → BLOCKED
- Credentials in output → Redacted

> Docs: docs/safety/SANDBOX.md
