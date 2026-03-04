## 2026-03-04 - Generic UI utility buttons need context

**Learning:** Generic utility buttons like "copy-btn" in Flow Studio rely heavily on visual proximity to adjacent text (like terminal commands). This causes screen reader users to hear only "Copy" without knowing *what* is being copied.

**Action:** Always explicitly add context-specific `aria-label` attributes to generic UI utility buttons in their HTML fragments to properly support screen readers.
