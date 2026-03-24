## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-03-24 - Efficient Directory Size Calculation
**Learning:** Using `pathlib.Path.rglob` to traverse directories recursively for calculating total size introduces significant performance overhead compared to `os.scandir`. Using `os.scandir` within a context manager recursively is much faster.
**Action:** When calculating directory metrics like total size, prefer `os.scandir` with `is_dir(follow_symlinks=False)` over `rglob` to optimize recursive traversal time.
