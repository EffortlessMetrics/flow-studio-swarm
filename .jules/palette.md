## 2024-05-23 - CSS-only Input States
**Learning:** Using `input:not(:placeholder-shown) ~ .sibling` allows toggling UI elements (like clear buttons or shortcuts) based on input value without JavaScript state listeners. This reduces JS complexity and layout thrashing.
**Action:** Use this pattern for all input-dependent icons/buttons (clear, search, shortcuts) instead of manually toggling classes in `input` event listeners.
