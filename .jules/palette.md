## 2024-05-22 - [Search Input Clear Button]
**Learning:** Inserted elements (like a clear button) must be placed *after* the input and its shortcut to preserve CSS adjacent sibling selectors (e.g. .search-input:focus + .search-shortcut).
**Action:** When modifying complex input groups, check for sibling selectors in CSS before changing DOM order.
