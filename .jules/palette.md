
## 2026-05-05 - Missing aria-expanded on Flow Studio toggle buttons
**Learning:** Found multiple instances of custom collapsible panels (Boundary Review, Routing Decisions) using chevron icons for toggling without updating `aria-expanded`. This is a common pattern in this app's components where visual state is maintained via classes but screen reader state is missing.
**Action:** Always add `aria-expanded` binding to the toggle button's template and explicitly update `target.setAttribute("aria-expanded", String(isExpanded))` in the toggle event handler alongside chevron text content updates.
