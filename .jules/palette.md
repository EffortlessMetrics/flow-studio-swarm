## 2024-05-24 - Semantic Button Focus Outlines
**Learning:** Custom interactive elements (like `.filter-btn`, `.run-control-btn`, etc) built in this app sometimes lack explicit `:focus-visible` CSS rules despite being semantic `<button>`s, leading to missing focus states during keyboard navigation.
**Action:** When auditing or creating custom UI elements, ensure explicit `:focus-visible` rules (e.g., `outline: 2px solid var(--fs-color-accent, #3b82f6); outline-offset: 2px;`) are added to maintain consistent keyboard accessibility.
