
## 2026-05-10 - Screen reader compatibility with inline form hints
**Learning:** Inputs using `span` for hints need an explicit `aria-describedby` reference to make it accessible to screen readers.
**Action:** Ensure inputs with hints have an `id` that can be mapped via `aria-describedby` for screen reader accessibility.
