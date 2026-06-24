## 2024-06-24 - Wrap literal text icons in screen reader accessible elements
**Learning:** Icon-only buttons using literal characters ('×', '?', '&times;') with aria-labels create double-reading issues if the text is not hidden. The aria-label reads the descriptive text, and the literal character may also be read unless wrapped in an element with aria-hidden="true".
**Action:** Always wrap text-based icons in `<span aria-hidden="true">` when the button has an `aria-label`.
