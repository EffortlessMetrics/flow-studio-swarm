## 2024-05-22 - Search Input Clear Button Pattern
**Learning:** Using CSS `:not(:placeholder-shown)` combined with sibling selectors (`~`) is a robust way to toggle visibility of input-adjacent controls (like clear buttons) without JavaScript event listeners for visibility state. This prevents flickering and simplifies the JS logic to just handling the action.
**Action:** Use this pattern for other input fields that need clear buttons or conditional actions.

## 2024-05-22 - UIID Registration
**Learning:** New UI elements in Flow Studio must be registered in both `domain.ts` (in `FlowStudioUIID` type) and `layout_spec.ts` (in the appropriate region) to ensure they are tracked for layout reviews and testing.
**Action:** Always update both files when adding new interactive elements with `data-uiid`.
