## 2024-05-22 - Unifying Keyboard Shortcuts
**Learning:** Found two competing classes for keyboard shortcuts: `.fs-kbd` (semantic but unstyled) and `.shortcut-key` (styled but used on spans).
**Action:** Unified on `<kbd class="fs-kbd">` with the enhanced styling. Prefer semantic tags + utility classes over component-specific classes for small UI atoms.
