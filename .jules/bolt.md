## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-03-23 - Directory Size Calculation Bottleneck
**Learning:** When recursively traversing directories to calculate metrics like total size, using `pathlib.Path.rglob` is significantly slower compared to a recursive implementation using `os.scandir`.
**Action:** Use `os.scandir` within a context manager (`with os.scandir(...) as it:`) to reliably release file descriptors, and pass `follow_symlinks=False` to `is_dir()` to prevent infinite loops when traversing the file system for calculations.