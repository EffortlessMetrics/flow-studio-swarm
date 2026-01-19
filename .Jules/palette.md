## 2026-01-19 - Interactive Divs vs Buttons
**Learning:** Legacy interactive `div` elements (with `role="button"`) are inferior to native `<button>` elements for accessibility. They require manual keyboard handling (Enter/Space) and focus management.
**Action:** When touching legacy UI code, replace interactive `div`s with `<button type="button">` and apply CSS resets (`background: none`, `border: none`, etc.) to maintain visual design while gaining native accessibility.
