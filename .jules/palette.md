## 2024-05-22 - Toggle Visibility with Sibling Selectors
**Learning:** Flow Studio uses `input:not(:placeholder-shown) ~ .element` to toggle visibility of helper elements (like shortcuts) based on input state without JS. This requires the helper element to appear *after* the input in the DOM.
**Action:** When adding clear buttons or other input-dependent controls, place them after the input and use the general sibling selector `~` to control visibility based on placeholder state.
