# Palette's Journal - UX & Accessibility Learnings

## 2025-05-27 - CSS-Only Input State Toggling
**Learning:** The CSS general sibling selector (`~`) combined with `:not(:placeholder-shown)` allows toggling the visibility of helper elements (like clear buttons or shortcuts) based on input value presence, without requiring JavaScript class manipulation on the input itself.
**Action:** When adding interactive helpers inside input containers, place them *after* the input in the DOM and use `input:not(:placeholder-shown) ~ .helper` to control their visibility. This reduces JS complexity and ensures the UI state is always in sync with the native input value.
