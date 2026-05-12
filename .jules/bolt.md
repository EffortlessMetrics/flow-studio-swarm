## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-12 - Optimize Directory Traversal
**Learning:** `Path.iterdir()` combined with `.is_dir()` instantiation is a significant bottleneck for large directories. Creating `Path` objects and forcing synchronous system stat calls is slow.
**Action:** Use `os.scandir()` instead to efficiently access cached OS metadata directly via `entry.is_dir()` and `entry.name`, reducing traversal time significantly.
