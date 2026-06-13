
## 2024-06-13 - Add aria-expanded to Routing Decision Card toggle
**Learning:** Found a custom collapsible component in `RoutingDecisionCard.js` that was missing `aria-expanded` state communication. When building custom expandable sections, we must always bind the `isExpanded` component state to the `aria-expanded` DOM attribute, otherwise screen readers have no context that the button toggles content visibility.
**Action:** Always include `aria-expanded` and `aria-controls` when implementing custom accordion/toggle patterns, and hide decorative arrows with `aria-hidden="true"`.
