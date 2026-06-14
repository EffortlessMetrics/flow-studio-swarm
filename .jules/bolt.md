## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-14 - Optimize Directory Traversal
**Learning:** Using `Path.iterdir()` with `is_dir()` and string sorting scales poorly on large directories because every path is constructed and individually `stat`ted. Using `os.scandir()` is much faster (often 4-5x) as directory entry stats are cached locally, which is crucial for tracking extensive backend runs histories.
**Action:** When directory traversal requires filtering based on stats (like `is_dir()`) and string-based comparisons, directly iterate over `os.scandir()` instead of using `pathlib.Path` structures until strictly necessary.
