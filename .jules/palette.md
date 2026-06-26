
## 2025-03-01 - Hide literal characters in icon-only buttons
**Learning:** When icon-only buttons use literal characters like "?", "×" with `aria-label`, screen readers redundantly announce both the description and the literal character.
**Action:** Wrap the literal character in `<span aria-hidden="true">` so only the descriptive `aria-label` is announced.
