# Secret Management

Secrets are toxic waste. Handle accordingly.

## Storage Hierarchy
1. **NEVER**: code, config files, logs, receipts, commits
2. **Local dev**: `.env` files (gitignored)
3. **Runtime**: environment variables
4. **Production**: Vault / Secret Manager

## Rotation Policy
- Immediate: on suspected exposure, personnel departure, security incident
- Scheduled: API keys 90 days, DB passwords 90 days, TLS certs before expiry

## The Rule
- Store secrets OUTSIDE the repository
- Pass via environment variables at runtime
- Rotate before they become liabilities
- Never log, never include in error messages

> Docs: docs/safety/SECRET_MANAGEMENT.md
