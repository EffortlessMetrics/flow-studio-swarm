# Secret Management

Secrets are toxic waste. Handle accordingly.

## Storage Hierarchy

1. **NEVER**: code, config files, logs, receipts, commits
2. **Local dev**: `.env` files (gitignored)
3. **Runtime**: environment variables
4. **Production**: Vault / Secret Manager

## Rotation Policy

- Immediate: suspected exposure, personnel departure, security incident
- Scheduled: API keys 90 days, DB passwords 90 days, TLS certs before expiry

## Detection

- Pre-commit hooks scan for known patterns
- CI scanning on every PR
- Flow 6 boundary scan before push

## On Detection

- BLOCK the operation
- Require removal before proceeding
- Never commit "we'll fix it later"

## On Exposure

1. REVOKE immediately (don't wait, don't assess first)
2. ROTATE (generate new, update all systems)
3. AUDIT (check access logs)
4. REMEDIATE (remove from history if needed)

## Rules

- Store secrets OUTSIDE the repository
- Pass via environment variables at runtime
- Redact from all output (logs, receipts, transcripts)
