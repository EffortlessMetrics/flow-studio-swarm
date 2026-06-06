
## 2026-06-06 - Add keyboard accessibility focus styles to modal close buttons and quick preset buttons
**Learning:** Found an accessibility issue pattern where several interactive button elements in modals lack `:focus-visible` styles, making keyboard navigation difficult to track visually for users relying on tabbing.
**Action:** Adding `:focus-visible` state styles to `.selftest-modal-close`, `#context-budget-modal .modal-close`, `.btn-preset`, and `#context-budget-modal .btn-secondary`/`.btn-primary` to ensure keyboard users see clear focus rings when navigating modals. I will prioritize `focus-visible` to avoid focus rings on mouse clicks.
