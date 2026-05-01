
## 2024-05-18 - Add ARIA expanded state to expand/collapse buttons
**Learning:** Screen reader users rely on `aria-expanded` and `aria-controls` to understand when a collapsible region has been opened or closed, but this is sometimes forgotten when creating custom expand/collapse components.
**Action:** Always ensure that custom expand/collapse buttons have an `aria-expanded` attribute that stays synced with the component's state, and an `aria-controls` attribute that points to the ID of the controlled region.
