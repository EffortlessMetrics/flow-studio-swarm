## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-16 - Use os.scandir over Path.iterdir
**Learning:** Path.iterdir() incurs unnecessary overhead from instantiating Path objects and stat() calls, whereas os.scandir() is significantly faster for directory traversal by yielding DirEntry objects with cached attributes.
**Action:** Opt for os.scandir() wrapped in a context manager when iterating through large directories to avoid performance bottlenecks.
