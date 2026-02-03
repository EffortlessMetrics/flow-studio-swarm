## 2024-10-10 - CSS-Only Input Clearing
**Learning:** Using `input:not(:placeholder-shown) ~ .clear-btn` allows toggling visibility of a clear button purely with CSS, reducing JS state complexity for the *visual* aspect.
**Action:** Use the sibling selector (`~`) pattern for input-adjacent controls to keep UI logic lightweight.
