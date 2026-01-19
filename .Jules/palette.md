## 2024-10-24 - Interactive div elements
**Learning:** Interactive elements implemented as `div`s with `cursor: pointer` are inaccessible to keyboard users and violate semantic HTML principles.
**Action:** Use `<button>` for interactive elements and style them to match the design (resetting default borders/backgrounds). For non-interactive elements, do not use `cursor: pointer` to avoid misleading users.
