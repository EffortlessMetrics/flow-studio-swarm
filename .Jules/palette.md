# Palette's Journal

## 2024-05-24 - Accessibility of Interactive Elements
**Learning:** Legacy interactive `div` elements are frequent in this codebase and should be replaced with semantic `<button>` elements. Adding ARIA roles to divs is insufficient; they lack native keyboard support and focus behaviors.
**Action:** When spotting `div`s with `onclick` handlers, refactor them to `<button>` tags, apply a reset class if necessary to maintain appearance, and ensure they have visible focus states.

## 2024-05-24 - Icon Button Accessibility
**Learning:** Icon-only buttons are often missing `aria-label` attributes, making them invisible to screen readers.
**Action:** Always verify that buttons without text content have a descriptive `aria-label`.

## 2024-05-24 - Styling Consistency
**Learning:** Inline styles are often used for small tweaks like border-radius on buttons, leading to visual inconsistency.
**Action:** Use utility classes like `.fs-icon-button` or `.fs-button-small` from `flow-studio.base.css` instead of inline styles.
