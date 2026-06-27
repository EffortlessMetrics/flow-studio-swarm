
## 2024-06-27 - Screen Reader Redundancy for Literal Icons
**Learning:** Using literal characters (like `?` or `×`) as icons in icon-only buttons causes screen readers to redundantly announce the character alongside the `aria-label`, confusing users.
**Action:** Always wrap literal text characters used as icons in `<span aria-hidden="true">` when the button already has an `aria-label`.
