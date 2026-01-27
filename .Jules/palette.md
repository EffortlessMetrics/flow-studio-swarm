## 2025-01-27 - [Semantic Keyboard Hints]
**Learning:** The `<kbd>` element with class `.fs-kbd` provides a consistent, borderless visual style for keyboard shortcuts in this design system, preferred over the legacy `.shortcut-key` class which had borders.
**Action:** Use `.fs-kbd` for all new keyboard shortcut hints. When refactoring, replace `.shortcut-key` with `.fs-kbd`.

## 2025-01-27 - [Decorative Emojis]
**Learning:** Flow Studio uses raw emoji characters in `div`s as icons (e.g. `\u{1F4C2}`). These are read by screen readers as text (e.g. "Open File Folder"), creating noise in empty states.
**Action:** Always add `aria-hidden="true"` to containers holding decorative emoji icons.
