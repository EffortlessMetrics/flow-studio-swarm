## 2026-02-01 - Reusable Pattern: Search Clear Button Visibility
**Learning:** A reliable, CSS-only pattern for toggling "clear" button visibility based on input state is using the `:placeholder-shown` pseudo-class combined with the general sibling combinator (`~`). This avoids complex JS state management for simple visibility toggles.
**Action:** When adding clear buttons to inputs, place the button *after* the input in the DOM and use `.input:not(:placeholder-shown) ~ .clear-btn { display: block; }`. Ensure the button is keyboard accessible (standard `<button>`) and has an `aria-label`.
