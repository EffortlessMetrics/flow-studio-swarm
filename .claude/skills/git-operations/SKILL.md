---
name: git-operations
description: Safe git operations for branch management and history. Use when working with branches, commits, or repo operations.
---
# Git Operations

1. Work on branches, never directly on main/master.
2. Keep commits atomic and buildable (tests pass at each).
3. No force-push to shared branches.
4. No secrets, credentials, or local paths in commits.
5. Use revert for upstream fixes, reset only in shadow fork.
6. Document any history changes with justification.
