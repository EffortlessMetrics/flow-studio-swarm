## 2025-02-28 - Icon Button Accessibility
**Learning:** Literal text characters like `×` and `?` used as icons are announced by screen readers, creating redundancy when an `aria-label` is present.
**Action:** Always wrap literal icon characters in `<span aria-hidden="true">` if the button already has an `aria-label`.
