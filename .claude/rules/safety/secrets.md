# Secrets

Secrets are toxic waste. Detect before escape. Respond immediately.

## Storage Hierarchy

1. **NEVER**: code, config files, logs, receipts, commits
2. **Local dev**: `.env` files (gitignored)
3. **Runtime**: environment variables
4. **Production**: Vault / Secret Manager

## Detection

- Pre-commit hooks scan for patterns
- CI scanning on every PR
- Flow 6 boundary scan before push

## On Detection

BLOCK the operation. Require removal. Never "fix later."

## On Exposure

1. **Revoke immediately** (don't assess first)
2. **Rotate** (new credentials, update all systems)
3. **Audit** (check access logs)
4. **Remediate** (remove from history if needed)

## The Rule

- Secrets in diff = BLOCKED at boundary
- Store outside repo, pass via env vars
- Rotate before they become liabilities
- Never log, never include in error messages

> Docs: docs/safety/SECRET_MANAGEMENT.md
