## 2025-02-27 - Search Input Clear Pattern
**Learning:** Using CSS `:not(:placeholder-shown) ~ .clear-btn` provides a robust, JS-free way to toggle visibility of input-adjacent elements like clear buttons. This reduces state management complexity in JS and ensures the UI is always in sync with the input value.
**Action:** Apply this pattern for other input fields that require conditional action buttons (e.g., password visibility toggle, filter inputs).
