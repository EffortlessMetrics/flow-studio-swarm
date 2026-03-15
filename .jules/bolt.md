## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Optimize Directory Size Calculation
**Learning:** Using `pathlib.Path.rglob("*")` combined with `entry.is_file()` and `entry.stat()` is significantly slower than using `os.scandir()`. `rglob` generates complete paths and `os.scandir` caches file type and stat information, making it over 3x faster for recursive directory size calculations.
**Action:** Replace `pathlib.Path.rglob("*")` with recursive `os.scandir()` and `entry.is_file()`/`entry.stat().st_size` for directory size aggregation to eliminate overhead.
