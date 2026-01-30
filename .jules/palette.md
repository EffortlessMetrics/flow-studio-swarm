# Palette's Journal

This journal tracks critical UX and accessibility learnings for Flow Studio.

## 2024-05-22 - [Search Clear Button]
**Learning:** Users expect a quick way to clear search inputs without backspacing.
**Action:** Implemented a clear button that appears when text is present, using CSS `:not(:placeholder-shown)` for efficient toggling without JS state management for visibility.
