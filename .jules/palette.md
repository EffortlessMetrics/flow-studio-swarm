## 2026-06-26 - Wrap literal characters in icon-only buttons with aria-hidden
**Learning:** When literal text characters (like '?' or '×') are used as icons within a button that already has an `aria-label`, screen readers will redundantly announce both the label and the character, creating a confusing experience.
**Action:** Always wrap literal character icons in a `<span aria-hidden="true">`, particularly when the parent button contains an `aria-label`.
