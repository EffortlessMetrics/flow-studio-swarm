# Palette's Journal

## 2024-10-24 - Accessibility of Tab Components
**Learning:** The application uses both static HTML buttons and dynamically generated span elements for tab interfaces. The dynamic generation replaces accessible static content with inaccessible spans upon interaction, causing a regression in accessibility.
**Action:** When dynamically rendering UI components that replace static content, ensure the dynamic version maintains or improves the accessibility features (semantic tags, ARIA roles) of the static version. Always verify that dynamic re-rendering doesn't downgrade the user experience.
