
## 2026-06-22 - Screen Reader Button State Redundancy
**Learning:** Static aria-labels on buttons with dynamic text content completely override the visible text for assistive technologies, hiding state updates like 'Copied!'. Also, icon-only buttons with literal text characters ('?', '×') cause redundant announcements unless the character is wrapped in an aria-hidden span.
**Action:** Always omit static aria-labels on buttons with dynamic text, and wrap literal text character icons in <span aria-hidden="true"> when the button already has an aria-label.
