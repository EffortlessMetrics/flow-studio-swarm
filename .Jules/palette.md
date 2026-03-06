
## 2025-03-05 - Context-Specific ARIA Labels for Generic Utility Buttons
**Learning:** In UIs with repetitive generic elements like "Copy" buttons scattered across different sections (e.g., headers, toolbars, list items), screen reader users hear only "Copy button" without understanding what will be copied.
**Action:** Always provide context-specific `aria-label`s for generic utility buttons. For example, instead of just `<button>Copy</button>`, use `<button aria-label="Copy make dev-check command to clipboard">Copy</button>` so users know exactly what action the button performs.
