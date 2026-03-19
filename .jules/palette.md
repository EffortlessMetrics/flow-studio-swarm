## 2024-05-24 - [Add explicit focus-visible styles to toggle groups]
**Learning:** [Custom interactive elements like .filter-btn lack explicit :focus-visible rules, despite being semantic <button>s. Outlines can overlap in toggle groups.]
**Action:** [Ensure explicit :focus-visible rules are added with negative outline-offset and relative positioning to maintain consistent keyboard accessibility.]