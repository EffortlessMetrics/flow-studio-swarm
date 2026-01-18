## 2026-01-18 - Missing ARIA Labels on Icon-Only Buttons
**Learning:** Found a pattern of icon-only buttons (remove tags, add/remove list items) in `NodeInspector.ts` lacking `aria-label` attributes. This makes them inaccessible to screen readers.
**Action:** Systematically check all icon-only buttons in component libraries for `aria-label` and `title` attributes.
