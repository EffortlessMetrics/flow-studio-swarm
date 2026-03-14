## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Optimize Directory Size Calculation
**Learning:** `pathlib.Path.rglob` is slow for calculating recursive directory sizes (O(N) with high constant factor overhead from `pathlib` object creation).
**Action:** Replace `pathlib.Path.rglob` with a recursive function using `os.scandir(dir_path)` to significantly improve performance when measuring directory sizes. Place `try...except OSError` blocks inside the iteration loop (around individual `stat()` and `is_dir()` calls) for accuracy. Use `follow_symlinks=False` for `is_dir()` to prevent infinite loops, but do not use it for `is_file()` or `stat()` to match original `Path.stat()` behavior.
