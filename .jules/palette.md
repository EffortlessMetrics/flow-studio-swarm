
## 2026-04-24 - Dynamic Search Accessibility Pattern
**Learning:** For dynamic search dropdowns where items are generated via JS and can be navigated via arrow keys, ensuring the container has `role="listbox"` must be paired with explicitly setting `role="option"` and dynamically updating `aria-selected` on the results. This makes the arrow-key navigation accessible to screen readers.
**Action:** Always check the dynamically generated HTML of search widgets to ensure `role="option"` and `aria-selected` are properly attached and synchronized with visual state changes.
