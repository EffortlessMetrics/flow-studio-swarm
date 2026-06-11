## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## $(date +%Y-%m-%d) - Refactored Path.iterdir to os.scandir for directory traversal
**Learning:** Calling `Path.iterdir()` combined with `Path.is_dir()` scales poorly because constructing `Path` objects and invoking `.stat()` per entry adds significant overhead. Utilizing `os.scandir()` avoids this by directly caching stat attributes on `DirEntry` objects, which proved up to 8x faster in `statsdb/rebuild.py` loops.
**Action:** Always favor `os.scandir()` with a context manager for traversing large directories (like `runs/`) and extract properties (like `.is_dir()`) directly from the `DirEntry`.
