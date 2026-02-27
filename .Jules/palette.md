## 2025-01-28 - Added "Copy" Button to Empty State
**Learning:** Hardcoding inline styles in JS/TS fragments creates significant technical debt and inconsistency with the design system. It is critical to verify build artifacts (JS/HTML) are updated alongside source files.
**Action:** Always prefer existing utility classes like `fs-button-small` or `fs-status-button`. If custom styling is needed, it should be defined in a CSS file, not in the TypeScript fragment. Ensure `pnpm run ts-build` and `make gen-index-html` are run before submitting frontend changes.
