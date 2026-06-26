
## 2024-06-26 - Prevent redundant screen reader announcements for literal character icons
**Learning:** Icon-only buttons using literal characters (like '?') with an `aria-label` cause screen readers to announce both the descriptive label and the character, creating a confusing, redundant experience.
**Action:** Always wrap literal text characters used as icons in `<span aria-hidden="true">` when the parent interactive element already provides an accessible name via `aria-label`.
