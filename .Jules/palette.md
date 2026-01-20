# Palette's Journal

## 2024-05-22 - Semantic Elements over ARIA
**Learning:** Found interactive `div` elements acting as buttons. Using native `<button>` elements is always preferred over `div` with `role="button"` and `onclick` because it handles keyboard focus and activation automatically.
**Action:** When finding interactive `div`s, refactor them to `<button>`s and reset styles as needed, rather than just adding ARIA roles.
