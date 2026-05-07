## 2026-05-07 - Inconsistent ARIA labels on utility buttons
**Learning:** Inline utility buttons like "Copy" often miss ARIA labels across different components, even if they have `title` attributes. Tooltips aren't enough for screen readers when the visible text is just "Copy".
**Action:** Always verify that small utility buttons (like copy/paste/refresh) include explicit `aria-label`s describing the exact action context.
