## 2024-06-20 - Hide decorative text icons from screen readers
**Learning:** Even when a button has a descriptive `aria-label`, some screen readers might still read out the literal text content (like "multiply" for a `×` character or "question mark" for a `?` character) if it's not explicitly hidden.
**Action:** When using literal characters as icons inside icon-only buttons that have an `aria-label`, wrap the literal character in a `<span aria-hidden="true">` to ensure screen readers only announce the intended label.
