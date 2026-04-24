## 2026-04-24 - Missing ARIA label on copy button in empty state
**Learning:** Icon-only buttons in empty state templates are easy to miss because they're dynamically rendered fragments. In `swarm/tools/flow_studio_ui/src/ui_fragments.ts`, the copy button for `make demo-run` has a title but lacks an `aria-label`.
**Action:** When auditing icon-only buttons, search beyond static HTML and check template literals in TypeScript files that generate UI fragments.
