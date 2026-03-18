## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-03-18 - Optimize get_dir_size with os.scandir
**Learning:** Using `Path.rglob` to recursively calculate directory sizes is slow because it creates many Path objects and does additional stat calls. Using `os.scandir` is much faster (over 2x speedup) for directory traversal.
**Action:** When calculating sizes or recursively traversing directories for performance-critical or bulk operations like garbage collection, use `os.scandir` instead of `Path.rglob`.