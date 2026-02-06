## 2025-05-19 - Clear Button Pattern for Inputs
**Learning:** Adding a clear button (`x`) to inputs improves usability but requires handling focus states and keyboard shortcuts. Using CSS sibling selector `~` with `:not(:placeholder-shown)` is a clean way to toggle visibility without JS state management for visibility.
**Action:** Adopt this pattern for other filter/search inputs: absolute position right, hidden by default, visible when input has value.
