## 2025-01-29 - Search Input Clear Pattern
**Learning:** The sibling combinator `input:not(:placeholder-shown) ~ .clear-btn` provides a CSS-only toggle for clear buttons that respects the input's state without needing JavaScript for visibility management. This aligns with "Good UX is invisible" by reducing JS complexity for state changes.
**Action:** Use this pattern for all filter/search inputs in Flow Studio to ensure consistent behavior and reduce layout shifts (by reserving space via padding).
