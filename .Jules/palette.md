## 2025-05-15 - CSS Visibility Toggle Constraints
**Learning:** Flow Studio relies on CSS sibling selectors (e.g., `input:not(:placeholder-shown) ~ .target`) for visibility toggles. Using the HTML `hidden` attribute on the target element can conflict with these selectors or require specific overrides.
**Action:** When implementing visibility toggles based on sibling state, avoid `hidden` attribute and rely solely on CSS `display` properties controlled by the sibling selector.
