
## 2026-06-21 - Screen Reader Redundancy in Icon-only Buttons
**Learning:** When icon-only buttons use literal text characters (like '×' or '&times;') as the icon and have an `aria-label`, screen readers will redundantly announce both the label and the literal character.
**Action:** Always wrap literal text characters acting as icons in a `<span aria-hidden="true">`, particularly when the button already has an `aria-label` to prevent redundant and confusing screen reader announcements.
