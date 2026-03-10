## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Efficient directory size calculation
**Learning:** For calculating recursive directory sizes efficiently, using a recursive function with `os.scandir` is faster than `pathlib.Path.rglob("*")`. `rglob` can be slow for large directories. Using `follow_symlinks=False` prevents infinite loops, double-counting, or aborting the entire directory traversal on broken symlinks. `try...except OSError` blocks should be placed *inside* the iteration loop around individual `stat()` calls rather than wrapping the entire loop to ensure accuracy.
**Action:** Always prefer `os.scandir` over `pathlib.Path.rglob("*")` or `iterdir()` for performance-critical path traversals where only basic stat data (size, type) is needed.
