## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-20 - os.scandir Optimization
**Learning:** Path.iterdir() instantiates Path objects for every entry before sorting, which is slow for large directories. os.scandir() avoids this allocation overhead.
**Action:** Use os.scandir() inside a context manager for fast directory traversal and sorting.
