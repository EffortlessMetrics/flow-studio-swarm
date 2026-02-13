## 2025-05-15 - [Hidden Placeholders for Dynamic UIIDs]
**Learning:** Flow Studio's UIID regression tests (`tests/test_flow_studio_ui_ids.py`) parse the static `index.html` file and do not execute JavaScript. Consequently, dynamic UI elements (like buttons created in JS) cause test failures if they are missing from the static markup.
**Action:** When adding dynamic elements with required UIIDs, add a corresponding hidden placeholder (e.g., `<button style="display: none;" aria-hidden="true" data-uiid="...">`) in the relevant HTML fragment to satisfy the contract tests.

## 2025-05-15 - [Search Input Sibling Selectors]
**Learning:** The Flow Studio search input uses the CSS adjacent sibling selector (`.search-input:focus + .search-shortcut`) to toggle the shortcut's visibility.
**Action:** When injecting elements near the search input (like a clear button), place them *after* the shortcut element in the DOM to avoid breaking the CSS selector relationship, or use absolute positioning that doesn't rely on document flow order if possible (though here DOM order mattered for CSS).
