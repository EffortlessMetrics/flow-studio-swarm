## 2024-06-25 - Improve accessibility of literal character icon buttons
**Learning:** Icon-only buttons that use literal text characters (e.g., '?' or '×') require an aria-hidden span wrapping the literal character when an aria-label is provided to prevent screen readers from redundantly reading both the label and the character.
**Action:** When creating icon-only buttons with literal characters, always wrap the character in `<span aria-hidden="true">` to improve screen reader experience.
