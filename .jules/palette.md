
## 2026-06-05 - Add focus ring for accessibility
**Learning:** Icon-only buttons or utility buttons like copy buttons often lack keyboard focus styles by default, making keyboard navigation difficult.
**Action:** Always add a `:focus-visible` state with `outline: 2px solid var(--fs-color-accent, #3b82f6)` to utility buttons to ensure accessibility.
