## 2026-05-12 - Added focus styles for accessibility
**Learning:** Found that custom elements like `<select>` and interactive buttons lack focus outlines making keyboard navigation difficult.
**Action:** Always add `:focus-visible` outlines to interactive elements to preserve visuals for mouse users while keeping accessibility for keyboard users.
