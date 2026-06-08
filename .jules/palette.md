## 2024-06-08 - Added Focus-Visible to Toggles
**Learning:** Found a widespread pattern where custom toggles and selectors (like view-toggle, mode-toggle, and run-selectors) lacked proper keyboard `focus-visible` states, relying entirely on hover states. This hides the active element from keyboard-only users.
**Action:** Adding consistent `focus-visible` standard styles globally using the accent color prevents these interactive elements from becoming inaccessible.
