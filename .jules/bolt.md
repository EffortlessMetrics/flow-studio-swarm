## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-11 - Fast Directory Traversal
**Learning:** When navigating large directories like runs_dir, `pathlib.Path.iterdir()` combined with `.is_dir()` instantiates objects and forces expensive synchronous system stat calls for every item. `os.scandir()` is significantly faster because it efficiently accesses cached OS metadata.
**Action:** Always evaluate `entry.is_dir()` and `entry.name` directly on the `os.DirEntry` object from `os.scandir()` before converting it to a Path object to avoid negating the performance benefits with new system calls.
