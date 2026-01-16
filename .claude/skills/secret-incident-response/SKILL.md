---
name: secret-incident-response
description: Handle secret exposure incidents. Use when credentials are leaked, committed to git, or detected in logs/outputs.
---
# Secret Incident Response

1. STOP: Block any further publishing immediately.
2. REVOKE: Invalidate the exposed credential (don't assess first).
3. ROTATE: Generate and deploy replacement credentials.
4. AUDIT: Check access logs for unauthorized usage.
5. REMEDIATE: Remove from git history if committed (BFG/filter-branch).
6. DOCUMENT: Record timeline, scope, and prevention measures.
