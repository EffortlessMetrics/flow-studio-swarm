## 2026-01-18 - Semantic Interactions
**Learning:** Legacy UI patterns often used `div`s with `cursor: pointer` for interactive elements (like badges), which excludes keyboard users and screen readers.
**Action:** Always replace interactive `div`s with `<button>` elements, ensuring to reset default styles (`border: none`, `background: none`) to maintain the visual design while gaining native accessibility.
