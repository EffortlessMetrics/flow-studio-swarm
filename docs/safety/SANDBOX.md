# Sandbox and Permissions

Autonomy requires isolation.

## Model

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

## Rules

- Operate inside repo/workspace only
- Avoid destructive commands unless explicitly required
- Prefer reversible edits and atomic writes
- If permission boundary is unclear: escalate
