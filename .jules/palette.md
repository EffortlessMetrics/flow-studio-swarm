## 2024-05-15 - Input Hint Accessibility Pattern
**Learning:** Input hints in modals are visually styled using the `.input-hint` class but lack programmatic association, causing screen readers to miss critical contextual information during form entry.
**Action:** Always pair `.input-hint` elements with `id` attributes and link them to their corresponding `<input>` elements using the `aria-describedby` attribute to ensure full context is announced to assistive technologies.
