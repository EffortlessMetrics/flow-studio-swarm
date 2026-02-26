## 2024-05-23 - Search Input UX Pattern
**Learning:** The search input lacked a clear way to reset, forcing users to manually delete text. Adding a clear button that appears only when text is present (via CSS sibling selectors `.input:not(:placeholder-shown) ~ .button`) provides a much better experience without complex JS state management for visibility.
**Action:** Use this CSS-driven visibility pattern for other input fields that require clearing or auxiliary actions.

## 2024-05-23 - Stale Build Artifacts
**Learning:** The `index.html` file in the repository was stale relative to the source code in `src/`. Running the build process (`make gen-index-html`) updated it, revealing changes (like semantic `button` elements replacing `div`s) that I didn't author but was responsible for committing.
**Action:** Always trust the build process to produce the source of truth for artifacts, and verify if "unexpected" changes are actually just syncing the repo to its true state.
