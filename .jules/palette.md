## 2024-05-24 - Screen reader redundancy
**Learning:** Screen readers redundantly announce icon-only text characters if they aren't hidden by `aria-hidden="true"` when an aria-label is present.
**Action:** Wrap literal text icons in `<span aria-hidden="true">`.
