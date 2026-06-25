
## 2026-06-25 - ARIA hidden attributes to prevent redundant screen reader announcements
**Learning:** When literal text elements like '?' or '×' act as an icon inside a button that already contains an `aria-label`, screen readers will audibly announce the `aria-label` as well as the text literal. This is confusing for visually impaired users.
**Action:** Add `aria-hidden="true"` to the literal character spans within `aria-label`ed buttons so the accessible label properly overrides the literal representation.
