
## 2024-06-28 - Hide literal question mark from screen readers in icon-only buttons
**Learning:** When improving accessibility for icon-only buttons that use literal text characters as icons (like `?`), the literal character must be wrapped in a `<span aria-hidden="true">` if the button already has an `aria-label`. Without this, screen readers will redundantly announce both the descriptive label and the literal character.
**Action:** Always wrap literal text characters acting as icons in `aria-hidden="true"` when adding or maintaining `aria-label`s on icon-only buttons.
