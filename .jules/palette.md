## 2025-05-15 - Keyboard Shortcuts Accessibility
**Learning:** Screen readers announce `aria-keyshortcuts` when focusing an element, but users who rely on visual cues or simple descriptions in `aria-label` also benefit from explicit text like "(Press /)". Combining both ensures broader coverage for different assistive technologies and user preferences.
**Action:** When adding keyboard shortcuts to interactive elements, include the shortcut in the `aria-label` (e.g., "Search (Press /)") AND use the `aria-keyshortcuts` attribute (e.g., `aria-keyshortcuts="/"`) for programmatic association.
