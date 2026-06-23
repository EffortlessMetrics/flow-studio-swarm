
## 2026-06-23 - Hide literal characters in icon-only buttons
**Learning:** When an icon-only button uses a literal text character (like '?' or '×') and already has an 'aria-label', screen readers will redundantly announce both the descriptive label and the character unless the character is wrapped in an 'aria-hidden' span.
**Action:** Always wrap literal text characters in `<span aria-hidden="true">` inside buttons that have an `aria-label` to prevent redundant screen reader announcements.
