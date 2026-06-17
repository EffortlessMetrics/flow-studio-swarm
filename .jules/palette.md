## 2026-06-17 - Add ARIA attributes to expandable sections
**Learning:** Expandable sections using simple icon toggles (▼/▶) need both `aria-expanded` to communicate state and `aria-label` to communicate purpose to screen reader users.
**Action:** Always include `aria-expanded` dynamically tied to the component's state and a descriptive `aria-label` for custom toggle buttons.
