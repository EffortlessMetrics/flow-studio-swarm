## 2024-05-22 - CSS-Only Input Clear Button Visibility
**Learning:** Flow Studio can utilize the `input:not(:placeholder-shown) ~ .clear-btn` CSS pattern to toggle visibility of helper elements without JavaScript state management. This requires using the general sibling selector (`~`) instead of adjacent (`+`) if other elements (like keyboard shortcuts) also depend on the input state.
**Action:** When adding input helpers, position them after the input in the DOM and use `~` selectors to manage their visibility based on input state.
