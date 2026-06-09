
## 2024-06-09 - Ensure generic buttons use focus-visible
**Learning:** Custom UI buttons without native button styling or with custom backgrounds often lack visible focus indicators, heavily hurting keyboard accessibility. Specifically using `:focus-visible` instead of `:focus` prevents annoying outlines when clicking while preserving them for keyboard users.
**Action:** Always verify keyboard navigation by tabbing through all custom interactive elements, and append `:focus-visible` with `outline` and `outline-offset` to the styling of custom buttons.
