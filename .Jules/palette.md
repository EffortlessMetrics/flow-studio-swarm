## 2025-05-15 - Standardizing Icon Buttons
**Learning:** The codebase lacked a consistent utility class for circular icon buttons, leading to repetitive inline styles and inconsistent sizing/hover states.
**Action:** Introduced `.fs-icon-button` in `flow-studio.base.css` to standardize size (24px), radius (50%), and hover effects. Use this class for all future icon-only actions in the header or toolbars.
