## 2024-03-05 - Missing ARIA Labels on Generic UI Buttons
**Learning:** Generic utility buttons like "Copy" in `flow_studio_ui` HTML fragments are visually clear but lack explicit `aria-label` attributes to properly describe their context (e.g., "Copy command X") for screen readers.
**Action:** When adding or updating utility buttons in Flow Studio, explicitly include context-specific `aria-label` attributes.
