
## 2026-06-16 - Global focus-visible fallbacks
**Learning:** Relying on component-specific `:focus-visible` rules often leaves gaps where interactive elements (like modal close buttons, dropdowns, inputs) lack keyboard focus indicators. It's safer to have a global fallback.
**Action:** Add a global `:focus-visible` rule for buttons, selects, and inputs in base CSS to ensure baseline keyboard accessibility across the app.
