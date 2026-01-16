# Secret Detection and Response

Detect before escape. Respond immediately.

## Detection Points
- Pre-commit hooks scan for known patterns (API keys, credentials, private keys)
- CI scanning on every PR
- Flow 6 boundary scan before push to upstream

## On Detection
- BLOCK the operation (commit/push/merge)
- Require removal before proceeding
- Never commit "we'll fix it later"

## On Exposure
1. **Revoke immediately** - don't wait, don't assess first
2. **Rotate** - generate new credentials, update all systems
3. **Audit** - check access logs for unauthorized usage
4. **Remediate** - remove from history if needed (filter-branch/BFG)

## The Rule
- Secrets in diff = BLOCKED at boundary
- Exposure = immediate revoke + rotate
- Redact secrets from all output (logs, receipts, transcripts)

> Skill: secret-incident-response
> Docs: docs/safety/SECRET_MANAGEMENT.md
