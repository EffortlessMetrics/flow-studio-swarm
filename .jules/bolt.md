## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Efficient Directory Traversal
**Learning:** When evaluating large numbers of directories, eagerly computing sizes using `pathlib.Path.rglob` is a performance bottleneck due to generator overhead and repeated stat calls.
**Action:** Use `os.scandir` recursively for efficient size calculations, caching system file types to avoid redundant stat calls entirely.
