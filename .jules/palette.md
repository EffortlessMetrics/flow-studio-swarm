## 2025-05-19 - Standardized Keyboard Shortcut Styling
**Learning:** Inconsistent usage of `<kbd>` vs `<span class="shortcut-key">` and duplicate CSS definitions led to visual discrepancies in keyboard hints across the UI.
**Action:** Standardized on `<kbd class="fs-kbd">` for all keyboard shortcuts. Updated `.fs-kbd` CSS to include a border and proper padding, matching the previous `.shortcut-key` style which was then removed. This ensures semantic correctness (using `<kbd>`) while maintaining visual polish.
