## 2024-05-18 - Generic UI Utility Buttons Context
**Learning:** Generic UI utility buttons (like copy-btn) in Flow Studio need explicitly defined context-specific `aria-label` attributes in their HTML fragments to properly support screen readers. They cannot just rely on `title` or visual context.
**Action:** Always verify generic icon or utility buttons have context-specific `aria-label`s instead of relying on generic "Copy" text.
