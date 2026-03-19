## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - pathlib.rglob overhead for large directories
**Learning:** `pathlib.Path.rglob` is significantly slower than `os.scandir` when calculating the total size of deep or heavily-populated directories, due to generator and path object creation overhead.
**Action:** When calculating metrics like total directory size via recursive traversal, use `os.scandir` directly instead. Ensure `follow_symlinks=False` is passed to `is_dir()` to avoid infinite loops, but not to `is_file()` or `stat()` to preserve original symlink sizing behavior.