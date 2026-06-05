
## 2026-06-05 - Keyboard Accessibility for Custom Interactive Elements
**Learning:** Custom buttons and toggles across the UI often lack proper `:focus-visible` states, severely hampering keyboard navigation.
**Action:** Always ensure all interactive elements (buttons, toggles, close buttons, action links) explicitly define a `:focus-visible` state (preferring it over `:focus` to avoid visual clutter on mouse clicks) utilizing an `outline` to guarantee keyboard accessibility.
