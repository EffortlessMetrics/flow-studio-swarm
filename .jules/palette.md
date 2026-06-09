## 2023-10-27 - Add Focus Visible Styles for Keyboard Navigation
**Learning:** This app's custom UI buttons and toggle components were relying entirely on hover states or generic outline-removal, making keyboard navigation virtually impossible to follow. The `:focus-visible` pseudo-class should be added to interactive elements to ensure accessibility without affecting mouse clicks.
**Action:** Next time, ensure all newly introduced interactive components (buttons, toggles, icon-buttons) include a specific `:focus-visible` outline property matching the app's accent color.
