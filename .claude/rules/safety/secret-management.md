# Secret Management: Lifecycle

**"Secrets are toxic waste. Handle accordingly."**

This rule covers secret lifecycle management: categorization, storage, and rotation. For detection and incident response, see [secret-detection-response.md](./secret-detection-response.md).

## Secret Categories

### API Keys

Provider-specific keys for external services.

| Provider | Pattern | Example Format |
|----------|---------|----------------|
| OpenAI | `sk-[A-Za-z0-9]{48}` | `sk-abc123...` |
| Anthropic | `sk-ant-[A-Za-z0-9-]{95}` | `sk-ant-api03-...` |
| GitHub (PAT) | `ghp_[A-Za-z0-9]{36}` | `ghp_abc123...` |
| GitHub (OAuth) | `gho_[A-Za-z0-9]{36}` | `gho_abc123...` |
| GitHub (App) | `ghs_[A-Za-z0-9]{36}` | `ghs_abc123...` |
| AWS Access Key | `AKIA[A-Z0-9]{16}` | `AKIAIOSFODNN7EXAMPLE` |
| AWS Secret Key | `[A-Za-z0-9/+=]{40}` | (40-char base64) |
| Slack | `xox[baprs]-[A-Za-z0-9-]+` | `xoxb-123-456-abc` |
| Stripe | `sk_live_[A-Za-z0-9]{24,}` | `sk_live_abc123...` |

### Credentials

Authentication for databases, services, and infrastructure.

| Type | Risk | Notes |
|------|------|-------|
| Database passwords | HIGH | Direct data access |
| Service account keys | HIGH | Often over-privileged |
| SSH private keys | CRITICAL | Infrastructure access |
| Cloud service credentials | HIGH | Resource control |

### Tokens

Short-lived or session-based authentication.

| Type | Lifetime | Notes |
|------|----------|-------|
| OAuth access tokens | Minutes-hours | Should auto-refresh |
| JWT signing keys | Long-lived | Rotation critical |
| Session tokens | Hours-days | Scope-limited |
| Refresh tokens | Days-weeks | Protect like credentials |

### Certificates

Cryptographic material for identity and encryption.

| Type | Risk | Rotation |
|------|------|----------|
| TLS private keys | HIGH | Annual or on compromise |
| Code signing certs | CRITICAL | Per security policy |
| CA certificates | CRITICAL | Rare, managed carefully |
| Client certs | MEDIUM | Per access policy |

---

## Storage Rules

### The Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│  NEVER: Code, config files, logs, receipts, commits    │
├─────────────────────────────────────────────────────────┤
│  LOCAL DEV: .env files (gitignored)                    │
├─────────────────────────────────────────────────────────┤
│  RUNTIME: Environment variables                        │
├─────────────────────────────────────────────────────────┤
│  PRODUCTION: Vault / Secret Manager                    │
└─────────────────────────────────────────────────────────┘
```

### Environment Variables (Runtime)

Secrets are passed via environment variables at runtime:

```bash
# Good: Set in shell, not in files
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GITHUB_TOKEN="ghp_..."

# Good: Read from environment in code
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise EnvironmentError("ANTHROPIC_API_KEY not set")
```

### .env Files (Local Dev Only)

For local development, use `.env` files that are gitignored:

```bash
# .env (MUST be in .gitignore)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
DATABASE_URL=postgresql://user:pass@localhost/db
```

**Required .gitignore entries:**
```gitignore
.env
.env.local
.env.*.local
*.env
.secrets
secrets/
```

### Vault / Secret Manager (Production)

Production environments use dedicated secret management:

| Service | Use Case |
|---------|----------|
| HashiCorp Vault | Self-hosted, enterprise |
| AWS Secrets Manager | AWS-native workloads |
| GCP Secret Manager | GCP-native workloads |
| Azure Key Vault | Azure-native workloads |
| 1Password (CLI) | Small teams, local dev |

### NEVER Store Secrets In

| Location | Why |
|----------|-----|
| Source code | Committed to history forever |
| Config files (checked in) | Same as code |
| Logs | Often aggregated, retained, searchable |
| Receipts | Audit trail should not contain secrets |
| Error messages | May be displayed or logged |
| Comments | Still in code |
| Documentation | May be public |
| Slack/email | Retained, searchable, forwarded |

---

## Rotation Policy

### Immediate Rotation (Suspected Exposure)

Rotate immediately if:
- Secret appears in logs, commits, or error output
- Secret was sent via insecure channel
- Personnel with access departs
- Security incident detected
- Secret found in public location

### Scheduled Rotation

| Secret Type | Rotation Period | Notes |
|-------------|-----------------|-------|
| API keys | 90 days or on exposure | Automate if provider supports |
| Database passwords | 90 days | Coordinate with deployment |
| Service accounts | 90-180 days | Audit usage before rotation |
| JWT signing keys | Annual | Requires token invalidation planning |
| TLS certificates | Before expiry (30-day buffer) | Automate with ACME/cert-manager |

### Token Lifecycle

Short-lived tokens should auto-refresh:

```python
# Good: Use refresh tokens, short-lived access tokens
class TokenManager:
    def __init__(self):
        self.access_token = None
        self.refresh_token = os.environ.get("REFRESH_TOKEN")
        self.expires_at = 0

    def get_token(self):
        if time.time() >= self.expires_at - 60:  # 60s buffer
            self._refresh()
        return self.access_token

    def _refresh(self):
        # Exchange refresh token for new access token
        response = self._call_token_endpoint()
        self.access_token = response["access_token"]
        self.expires_at = time.time() + response["expires_in"]
```

---

## The Rule

> Secrets are toxic waste.
> Store them outside the repository.
> Rotate them before they become liabilities.

## Enforcement Points

| Check | When | Action |
|-------|------|--------|
| Pre-commit hook | Before commit | Block if pattern matches |
| CI secret scan | On PR | Fail PR if detected |
| Flow 6 boundary | Before push | Block push if detected |
| Receipt generation | Always | Redact before write |
| Log output | Always | Redact before write |

---

## See Also

- [secret-detection-response.md](./secret-detection-response.md) - Detection patterns and exposure response
- [boundary-automation.md](./boundary-automation.md) - Publish gate checks
- [sandbox-and-permissions.md](./sandbox-and-permissions.md) - Containment model
- [git-safety.md](./git-safety.md) - Git operations safety
