
## 2024-10-24 - Add aria-hidden to literal text icons
**Learning:** Icon-only buttons using literal text characters (like ? or ×) need aria-hidden="true" on the text node if they already have an aria-label, to prevent redundant announcements by screen readers.
**Action:** Always wrap literal text icons in aria-hidden="true" spans when the button has an aria-label.
