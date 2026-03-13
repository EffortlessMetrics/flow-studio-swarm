## 2024-03-13 - Add focus rings to custom interactive elements
**Learning:** Custom interactive elements (like `.filter-btn` and `.collapse-toggle` semantic `<button>`s) often lack explicit `:focus-visible` CSS rules, making keyboard navigation difficult to track.
**Action:** Ensure explicit `:focus-visible` rules (e.g., `outline: 2px solid var(--fs-color-accent, #3b82f6); outline-offset: 2px;`) are systematically added to all interactive elements to maintain consistent keyboard accessibility.
