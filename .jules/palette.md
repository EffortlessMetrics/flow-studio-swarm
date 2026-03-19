## 2026-03-19 - Missing :focus-visible on custom elements
**Learning:** Custom interactive elements like `.filter-btn` and `.view-toggle button` often lack explicit `:focus-visible` CSS rules, reducing keyboard accessibility.
**Action:** Ensure explicit `:focus-visible` rules (e.g., `outline: 2px solid var(--fs-color-accent, #3b82f6);`) are added, using negative `outline-offset` and `position: relative; z-index: 1;` for toggle groups to avoid overlap.
