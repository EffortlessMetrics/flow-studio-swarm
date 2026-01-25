## 2025-05-15 - Standardizing Keyboard Hints
**Learning:** The application had inconsistent keyboard hint styling, using both unstyled `<kbd>` and `<span class="shortcut-key">`. A dedicated `.fs-kbd` class existed but was underutilized.
**Action:** Standardized all keyboard hints to use `<kbd class="fs-kbd">` and updated the CSS to be more consistent with the design system (added border/shadow). Future UI additions should strictly use this class for any key combinations.
