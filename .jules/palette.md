## 2024-03-14 - Ensure keyboard accessibility for custom buttons
**Learning:** Custom interactive elements (like `.filter-btn`) may lack explicit `:focus-visible` CSS rules despite being semantic `<button>`s.
**Action:** When auditing or creating custom UI elements, ensure explicit `:focus-visible` rules (e.g., `outline: 2px solid var(--fs-color-accent, #3b82f6); outline-offset: 2px;`) are added to maintain consistent keyboard accessibility.
