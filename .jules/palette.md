
## 2024-06-23 - Hide literal icon characters
**Learning:** Icon-only buttons with literal characters and an `aria-label` cause screen readers to announce both.
**Action:** Wrap the literal characters in `<span aria-hidden="true">`.
