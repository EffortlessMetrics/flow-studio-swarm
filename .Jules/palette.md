## 2024-05-22 - [Standardizing Async Toggles]
**Learning:** Dynamic content toggles (like "Load Events") often change text content but miss `aria-expanded` state, confusing screen readers about whether content is visible. Also, error handling in these toggles often leads to inconsistent UI states (e.g., "Retry" button that collapses the section).
**Action:** Created `setupAsyncToggle` utility to standardize `aria-expanded`, `aria-controls`, disabled states, and error handling for async content loading. Use this for all future async toggle buttons.
