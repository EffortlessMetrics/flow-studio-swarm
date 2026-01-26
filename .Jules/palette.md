# Palette's UX Journal

## 2024-10-24 - Semantic Keyboard Shortcuts
**Learning:** The codebase had inconsistent styling for keyboard shortcuts (`.shortcut-key` vs `.fs-kbd`), where `.fs-kbd` (the newer standard) uses CSS variables for font consistency while the deprecated class hardcoded them.
**Action:** When standardizing UI elements, check for "deprecated" notes in memory/docs and remove the old implementation completely to prevent regression. Also, ensure decorative icons in empty states have `aria-hidden="true"` to reduce screen reader noise.
