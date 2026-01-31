## 2025-01-31 - Clear Button Pattern
**Learning:** Input-adjacent actions (like clear buttons) can be toggleable purely via CSS using the `:placeholder-shown` pseudo-class and sibling combinators, but require careful DOM ordering (input -> button -> shortcut) and correct selectors (`~` vs `+`).
**Action:** When adding helper actions to inputs, place them after the input in DOM, use `~` for robustness, and ensure the JS handler dispatches a fresh `input` event to trigger state updates (like debouncers).
