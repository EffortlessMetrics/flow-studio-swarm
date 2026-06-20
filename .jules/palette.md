
## 2026-06-20 - Prevent Redundant Screen Reader Announcements in Icon-Only Buttons
**Learning:** When an icon-only button contains a literal text character (like '×' or '+') acting as an icon, and the button already has an `aria-label` for screen readers, the literal character should be wrapped in a `<span aria-hidden="true">`. Otherwise, screen readers will redundantly announce both the descriptive label and the literal character.
**Action:** Always wrap literal text characters acting as icons in `aria-hidden="true"` when their parent element already has a descriptive `aria-label`.
