## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Faster Directory Size Calculation
**Learning:** When recursively traversing directories to calculate metrics like total size, replacing `pathlib.Path.rglob` with `os.scandir` yields significantly better performance (approx 3x faster) by avoiding path object instantiation.
**Action:** Use `os.scandir` for performance-critical directory traversal. Ensure `follow_symlinks=False` is passed to `is_dir()` to prevent infinite loops, but do not pass it to `is_file()` or `stat()` to preserve original symlink sizing behavior.