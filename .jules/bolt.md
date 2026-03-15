## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Optimize Directory Size Traversal
**Learning:** `pathlib.Path.rglob("*")` is unexpectedly slow for calculating full directory sizes because it internally creates heavy `Path` objects for every single file. Furthermore, eagerly calculating directory sizes for a large number of directories during basic discovery operations compounds this bottleneck significantly.
**Action:** For performance-critical file system traversal, always prefer `os.scandir()`. When aggregating metadata that is not always needed, use lazy evaluation (e.g. `@property` with a backing cached field) instead of eagerly calculating it during object initialization.
