## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-03-15 - Optimize Directory Traversal
**Learning:** `pathlib.Path.rglob` has significant overhead due to object instantiation and internal generator logic, making it a bottleneck for bulk operations traversing thousands of files (e.g., calculating sizes in runs_gc.py).
**Action:** For performance-critical bulk traversals, replace `rglob` with a recursive `os.scandir` loop. Use `follow_symlinks=False` on `is_dir()` to avoid infinite loops, but retain default behavior on `is_file()` and `stat()` for accuracy. Wrap operations in `try...except OSError` inside the loop.