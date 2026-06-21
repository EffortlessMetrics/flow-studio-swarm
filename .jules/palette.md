## 2024-05-24 - Screen Reader Announcement of Literal Characters
**Learning:** When literal text characters (like '?' or '×') are used inside an icon-only button, screen readers may redundantly announce both the descriptive aria-label and the literal character.
**Action:** Always wrap the literal character in an `<span aria-hidden="true">` if the button already has an aria-label to prevent double announcements.
