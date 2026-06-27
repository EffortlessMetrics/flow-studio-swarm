
## 2026-06-27 - Redundant Screen Reader Announcements on Literal Icons
**Learning:** Screen readers announce both the descriptive aria-label and the literal text character (like '?') used as an icon, creating redundant and confusing auditory experiences.
**Action:** Always wrap literal text characters used as icons in a `<span aria-hidden="true">` when the parent button already provides an `aria-label`.
