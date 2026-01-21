## 2026-01-21 - [Reusable Icon Button Pattern]
**Learning:** Reusable circular icon buttons (like 'Help' or 'Close') should not use inline styles but a dedicated utility class for consistency and maintainability.
**Action:** Use `.fs-icon-button` in `flow-studio.base.css` for any circular icon-only buttons instead of repeating `border-radius: 50%` and flex styles inline.
