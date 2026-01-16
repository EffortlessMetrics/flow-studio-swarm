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

Revoke immediately → Rotate → Audit → Remediate. Don't assess first—assume compromise.

## The Rule

- Secrets in diff = BLOCKED at boundary
- Store outside repo, pass via env vars
- Rotate before they become liabilities
- Never log, never include in error messages

> Docs: docs/safety/SECRET_MANAGEMENT.md
