## 2024-05-14 - Improve accessibility of interactive elements
**Learning:** Some interactive buttons like "Copy" in the inspector or code blocks do not have `aria-label`s, which can make it hard for screen reader users to identify their purpose out of context. The same applies to various close buttons in modals.
**Action:** Add clear `aria-label`s to all icon-only or generic-text interactive elements, particularly "Copy" buttons.
