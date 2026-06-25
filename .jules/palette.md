## 2025-02-27 - Prevent redundant screen reader announcements
**Learning:** Icon-only buttons using literal text characters with an aria-label cause redundant announcements if the character is not hidden.
**Action:** Wrap literal characters in <span aria-hidden="true"> when an aria-label is present.
