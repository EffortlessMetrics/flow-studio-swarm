## 2026-05-13 - Icon-only Copy Buttons Need Context
**Learning:** Icon-only buttons (like copy buttons) that rely solely on `title` attributes are insufficient for screen readers. The `title` attribute is often inconsistently announced by different screen readers.
**Action:** Always provide an explicit `aria-label` for icon-only buttons to clarify their intent (e.g., "Copy dev-check command to clipboard" instead of just "Copy").
