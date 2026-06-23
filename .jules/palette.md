
## 2024-10-24 - Redundant Text in Aria-Labeled Buttons
**Learning:** When improving accessibility for icon-only buttons that use literal text characters as icons (like '?' or '×'), screen readers can redundantly announce the descriptive label alongside the character if the character is not hidden. I found this pattern to be present in modal close buttons and help toggles.
**Action:** Wrap the literal character in a `<span aria-hidden="true">` element if the button already has a comprehensive `aria-label` to prevent redundant and confusing screen reader announcements.
