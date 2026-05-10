
## 2026-05-10 - Dynamic ARIA States in Vanilla JS Components
**Learning:** Dynamically rendered components constructed with template literals easily drop ARIA state synchronization because their HTML strings don't automatically bind to state variables like `isExpanded`.
**Action:** When adding ARIA states (like `aria-expanded`) to dynamic templates, always ensure the event listener explicitly updates the DOM attributes (`setAttribute`) alongside the textual/visual changes.
