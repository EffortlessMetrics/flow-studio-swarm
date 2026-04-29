## 2024-05-18 - Improve ARIA labels for copy buttons
**Learning:** Icon-only buttons or buttons with generic text like "Copy" lack context for screen reader users when navigating outside the visual flow.
**Action:** Always provide specific `aria-label` attributes to clarify the exact action being performed (e.g., `aria-label="Copy make dev-check command"` instead of just "Copy").
