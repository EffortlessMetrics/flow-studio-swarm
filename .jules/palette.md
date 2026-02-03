## 2024-10-24 - Sibling Selector Fragility
**Learning:** Using adjacent sibling selectors (`+`) for visibility toggles (e.g., hiding a shortcut hint when input is active) is brittle. Injecting a new element (like a clear button) between the input and the target breaks the selector without any obvious error, leading to UI regressions.
**Action:** Prefer general sibling selectors (`~`) when the exact DOM order might change or when "input-adjacent" elements need to be toggled, provided the target still follows the trigger in the DOM.
