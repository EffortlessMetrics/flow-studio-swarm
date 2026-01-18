## 2024-01-18 - Accessibility Retrofit Pattern
**Learning:** Legacy UI elements (like status badges) often use `div` + `click` handler without keyboard support. This is a common pattern in the vanilla TS codebase.
**Action:** When touching these elements, always upgrade them to `role="button"` + `tabindex="0"` and add a `keydown` listener for Enter/Space. Do not leave them as mouse-only.
