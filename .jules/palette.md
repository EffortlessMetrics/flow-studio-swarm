## 2024-03-09 - Missing aria-labels on generic copy buttons
**Learning:** Found that generic `copy-btn` utility buttons in Flow Studio lack specific aria-labels (e.g., in inspector). Since the visual text is just "Copy", screen readers lose context of *what* is being copied if the aria-label isn't explicitly set with context.
**Action:** When adding utility buttons like `copy-btn`, explicitly provide a contextual `aria-label` like "Copy generation command to clipboard".
