
## 2026-06-25 - Hide Literal Characters in Accessible Buttons
**Learning:** Literal characters used as icons inside buttons with an existing `aria-label` should be wrapped in `<span aria-hidden="true">`. Otherwise, screen readers may redundantly announce the descriptive label alongside the literal character, causing a confusing experience.
**Action:** Always wrap literal icon characters (like '?' or '×') with `aria-hidden="true"` when the parent button provides a descriptive `aria-label`.
