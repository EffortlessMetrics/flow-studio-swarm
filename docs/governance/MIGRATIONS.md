# Migrations

Migrations must be executable and reversible.

## Requirements

- Migration steps are numbered and testable
- Tooling is idempotent and supports dry-run
- Logs are captured to evidence paths
- Rollback exists for destructive steps

## If Tooling Cannot Be Provided

Document manual steps and set risk explicitly.

## Migration Guide Template

1. **Summary**: What's changing
2. **Prerequisites**: What must be true before starting
3. **Steps**: Numbered, one action per step
4. **Verification**: How to confirm success
5. **Rollback**: How to undo if needed
6. **Troubleshooting**: Common issues and fixes
