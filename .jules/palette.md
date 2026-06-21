
## 2024-06-21 - Screen Reader Redundancy in Icon Buttons
**Learning:** When icon-only buttons use literal characters (like '?' or '×') without aria-hidden, screen readers redundantly announce both the aria-label description and the literal character.
**Action:** Always wrap literal text characters serving as icons in <span aria-hidden="true"> when the button already has an aria-label.
