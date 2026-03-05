## 2023-11-20 - [Context-Specific ARIA Labels for Utility Buttons]
**Learning:** Generic utility buttons like "Copy" might exist in the DOM multiple times. While their visual context (e.g. being next to a code snippet) clarifies their purpose to sighted users, screen readers will just read "Copy button".
**Action:** When creating or adding utility buttons (e.g., `<button class="copy-btn">Copy</button>`), explicitly add `aria-label`s describing *what* is being copied (e.g., `aria-label="Copy make dev-check command to clipboard"`).
