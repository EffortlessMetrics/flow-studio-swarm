
## 2024-06-24 - Hide literal icon text in aria-labeled buttons
**Learning:** When using literal characters like '?' or '×' as icons in buttons that already have an `aria-label`, screen readers will redundantly read both the label and the literal character. Wrapping the literal character in `<span aria-hidden="true">`, which is already used in other parts of the application, solves this.
**Action:** Always wrap literal text characters acting as icons in `<span aria-hidden="true">` if the parent element provides the accessible name via `aria-label`.
