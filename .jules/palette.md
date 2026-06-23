## 2026-06-23 - Hide raw text characters in aria-labeled buttons
**Learning:** Raw text characters used as icons inside buttons with aria-labels should be hidden to prevent redundant screen reader announcements.
**Action:** Always wrap literal character icons in <span aria-hidden="true"> when the parent button already has a descriptive aria-label.
