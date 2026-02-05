
## 2026-02-05 - CSS-Only Input Visibility Toggles
**Learning:** You can toggle visibility of input-adjacent elements (like clear buttons or shortcuts) using `.input:not(:placeholder-shown) ~ .target`. This avoids JS state management for simple visibility logic but requires careful DOM ordering (target must follow input).
**Action:** Use this pattern for clear buttons, helper text, or validation icons that depend on input state.
