
## 2026-06-27 - Added aria-hidden to redundant text character in icon-only help button
**Learning:** When an icon-only button uses a literal text character (like `?`) as its icon and also provides a descriptive `aria-label`, screen readers will redundantly announce both the descriptive label and the literal character if the character is not explicitly hidden. This creates a cluttered and confusing experience for users relying on assistive technologies.
**Action:** Always wrap literal text characters serving as icons in `<span aria-hidden="true">` when the parent button or element already has an `aria-label` providing the primary descriptive context.
