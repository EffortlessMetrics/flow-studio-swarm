---
name: secret-rotation
description: Rotate secrets and credentials safely. Use when rotating API keys, passwords, or handling scheduled credential updates.
---
# Secret Rotation

1. Identify the secret type and all systems using it.
2. Generate new credentials in the secret store.
3. Deploy new credentials to dependent systems.
4. Verify systems work with new credentials.
5. Revoke old credentials.
6. Document rotation in audit log with timestamp.
