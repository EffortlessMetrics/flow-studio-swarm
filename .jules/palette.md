
## 2024-11-20 - Accessible Accordion Toggles
**Learning:** Custom collapsible sections (like candidate rejections in decision cards) frequently miss `aria-expanded` bindings, leaving screen reader users unaware of their state. Additionally, text-based icons (like `▼` or `▶`) create noise if not hidden with `aria-hidden="true"`.
**Action:** Always bind `aria-expanded` to the expanded state variable, and explicitly hide decorative arrow spans from screen readers.
