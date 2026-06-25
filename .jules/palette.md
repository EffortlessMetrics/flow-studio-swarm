
## 2024-05-24 - Screen Reader Redundancy on Literal Icons
**Learning:** Icon-only buttons that use literal text characters (like '?' or '×') and also have an `aria-label` cause screen readers to read both, creating redundant and confusing noise.
**Action:** Always wrap literal text icons in `<span aria-hidden="true">`, especially when the parent interactive element already provides an `aria-label`.
