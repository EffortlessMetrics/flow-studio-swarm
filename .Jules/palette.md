## 2024-05-18 - Missing context on generic utility buttons
**Learning:** Generic UI utility buttons (like `copy-btn` in Flow Studio) often lack meaningful text context for screen readers when they only contain generic terms like "Copy" or an icon.
**Action:** Explicitly include context-specific `aria-label` attributes (e.g., `aria-label="Copy make dev-check command"`) in HTML fragments to properly support screen readers.
