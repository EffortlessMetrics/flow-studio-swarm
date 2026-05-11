## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-11 - Optimize Directory Traversal Performance
**Learning:** Using `pathlib.Path.iterdir()` chained with `.is_dir()` on large directories causes substantial overhead because it creates redundant `Path` objects and executes blocking synchronous system `stat()` calls per item.
**Action:** Refactor performance-critical directory iteration bottlenecks to use `os.scandir()` which returns cached OS-level metadata `(is_dir(), name)` natively. Ensure `entry.is_dir()` is checked prior to reconverting `entry.path` back to `Path` objects for downstream compatibility.
