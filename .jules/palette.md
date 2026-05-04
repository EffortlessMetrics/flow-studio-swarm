
## 2024-05-04 - Expand/Collapse Accessibility
**Learning:** Custom expand/collapse buttons often lack `aria-expanded` and `aria-controls` attributes, leaving screen reader users blind to their state and what they control.
**Action:** Always ensure custom toggles have `aria-expanded` synced with their state and `aria-controls` pointing to the ID of the collapsible content.
