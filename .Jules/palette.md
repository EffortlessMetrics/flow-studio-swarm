## 2024-05-22 - Consistent Command Copying
**Learning:** The `createQuickCommands` utility in `utils.ts` provides a consistent, accessible way to display copyable shell commands. It should be used over ad-hoc HTML construction to ensure consistent styling and behavior (e.g. "Copied!" feedback).
**Action:** Always prefer `createQuickCommands` or `createPathWithCopy` when displaying paths or commands in details panels.
