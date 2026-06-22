## 2024-06-22 - Hide icon-only button text for screen readers
**Learning:** Icon-only buttons with explicit \`aria-label\` attributes that use literal characters (like \`×\` or \`&\#215;\`) as the icon need those characters wrapped in \`aria-hidden="true"\`. Otherwise, screen readers announce both the descriptive aria label and the literal character.
**Action:** Always wrap visual text icons inside icon-only buttons with \`span aria-hidden="true"\` when an aria-label provides the accessible name.
