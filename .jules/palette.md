## 2026-05-07 - Dynamic Aria Attributes
**Learning:** Toggle buttons with dynamic states (expand/collapse) need their `aria-expanded`, `aria-label`, and `title` attributes to update dynamically to accurately reflect their state to screen readers.
**Action:** Always bind accessibility attributes to the same boolean state (`isExpanded`) used for rendering the visual toggle icon.
