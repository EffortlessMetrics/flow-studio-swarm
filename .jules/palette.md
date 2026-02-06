## 2026-02-06 - CSS-Only Input Clear Button
**Learning:** Flow Studio uses the general sibling selector (`.input:not(:placeholder-shown) ~ .target`) to toggle visibility of input-adjacent elements without JavaScript. This is robust for search inputs where "clear" buttons should only appear when text is present.
**Action:** Use this pattern for future input controls to reduce JS state management complexity.
