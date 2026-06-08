
## 2024-06-08 - Keyboard accessibility focus rings
**Learning:** When adding focus styles to interactive UI elements to satisfy keyboard navigation a11y, using `:focus-visible` over `:focus` is strictly preferred. It ensures focus rings display for keyboard users while staying hidden during mouse clicks, preserving visual layout.
**Action:** Always favor `:focus-visible` over `:focus` when styling `.btn` or similar interactive UI elements.
