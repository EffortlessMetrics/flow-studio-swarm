## 2026-05-08 - Accessible Expand/Collapse Buttons
**Learning:** Icon-only expand/collapse buttons (like "▼" or "▶") are opaque to screen readers without proper attributes. They require `aria-expanded` to indicate state, `aria-controls` to link to the controlled region, and `aria-label` to clearly state their action.
**Action:** Always pair visual state indicators on toggle buttons with programmatic `aria-expanded` attributes, and ensure they have descriptive `aria-label`s when lacking visible text.
