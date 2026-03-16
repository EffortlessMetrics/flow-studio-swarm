## 2024-05-24 - Missing Focus Indicators on Interactive Elements

**Learning:** Custom interactive elements like `.filter-btn`, `.view-toggle button`, and `.mode-toggle button` lack explicit `:focus-visible` CSS rules despite being semantic `<button>`s, leading to poor keyboard accessibility as users cannot track focus.

**Action:** Ensure explicit `:focus-visible` rules (e.g., `outline: 2px solid var(--fs-color-accent, #3b82f6);`) are added when creating or auditing custom interactive components to maintain consistent keyboard accessibility. Negative `outline-offset` and `position: relative; z-index: 1;` might be necessary for elements acting as toggle groups to avoid outline overlapping issues.