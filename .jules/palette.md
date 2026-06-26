
## 2026-06-26 - Adding ARIA span for icon-only button
**Learning:** When improving accessibility for icon-only buttons that use literal text characters as icons (e.g., '?') and already have an aria-label, the literal character must be wrapped in a <span aria-hidden="true">. Otherwise, screen readers may redundantly announce both the descriptive label and the literal character.
**Action:** Always verify if an icon-only button with literal text characters has an aria-label and ensure the literal characters are appropriately hidden from screen readers using aria-hidden.
