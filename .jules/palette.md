# Palette Journal

## 2024-03-24 - Interactive Component Focus States
**Learning:** Flow Studio UI extensively uses custom interactive elements (like `.filter-btn` in run history) built as semantic `<button>`s, but these elements frequently lack `.element:focus-visible` CSS rules. While mouse hover states (`:hover`) are generally implemented, keyboard focus visibility is easily overlooked when components aren't explicitly inheriting focus styles from `.fs-button-small` or `.fs-icon-button`.
**Action:** When auditing custom UI elements (especially those in isolated CSS sections like `.run-history-filter`), ensure that explicit `:focus-visible` rules (e.g., `outline: 2px solid var(--fs-color-accent, #3b82f6); outline-offset: 2px;`) are added to maintain consistent keyboard accessibility.
