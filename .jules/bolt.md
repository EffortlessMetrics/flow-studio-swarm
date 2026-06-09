## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-02-27 - Optimizing Directory Traversal
**Learning:** Using pathlib.Path.iterdir() combined with .is_dir() on large directories instantiates path objects and forces expensive synchronous system stat calls for every item. os.scandir() is significantly faster as it caches OS metadata.
**Action:** Use os.scandir() instead of Path.iterdir() when iterating over large directories to improve performance, while being careful to only instantiate Path objects when strictly necessary.
