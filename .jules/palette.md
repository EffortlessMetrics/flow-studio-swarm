## 2024-05-24 - Brittle CSS Combinators
**Learning:** Flow Studio CSS relies heavily on adjacent sibling combinators (`+`) for visibility toggles (e.g., input + shortcut), which breaks when injecting helper elements like clear buttons.
**Action:** Prefer general sibling combinators (`~`) for visibility toggles to allow flexible DOM ordering and element injection.
