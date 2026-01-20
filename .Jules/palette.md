# Palette's Journal 🎨

## 2026-01-20 - Standardizing Icon Buttons
**Learning:** Found inconsistent inline styles for circular icon buttons (like the help button), leading to potential visual drift and missed accessibility states (focus-visible).
**Action:** Introduced `.fs-icon-button` utility class in `flow-studio.base.css` to centralize styling for circular actions. Replaced inline styles in header. Next time: look for other inline-styled buttons to migrate.
