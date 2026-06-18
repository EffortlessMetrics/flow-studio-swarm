## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Avoid Path.iterdir() in performance-critical loops
**Learning:** `Path.iterdir()` has significant overhead because it instantiates `Path` objects and computes path components like `suffix` and `stem` for every entry. `os.scandir` is ~8x faster as it yields lightweight `DirEntry` objects with cached attributes.
**Action:** Use `os.scandir` when iterating over directories in high-frequency functions or when iterating over large directories.
