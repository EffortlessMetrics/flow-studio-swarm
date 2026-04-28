## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-03-08 - Avoid deepcopy on nested dataclasses
**Learning:** Using `copy.deepcopy` on heavily nested dataclasses (like `NavigatorOutput`) is a significant performance anti-pattern, causing up to a 10x slowdown compared to manual instantiation.
**Action:** Implement and use custom `.clone()` methods that manually construct new instances and perform shallow copies on internal collections instead of relying on `deepcopy`.
