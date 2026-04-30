## 2026-04-30 - Add aria-expanded to expandable boundary review button
**Learning:** Found a missing `aria-expanded` state on the `toggle-expand` button in the boundary review component, making it difficult for screen readers to know if the sections are collapsed or expanded.
**Action:** Consistently add `aria-expanded` boolean attributes to expand/collapse buttons and ensure the JS event listener updates the property so screen readers have an accurate, sync'd state.
