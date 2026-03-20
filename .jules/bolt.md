## 2026-01-23 - Use os.scandir for directory traversal
**Learning:** Calculating directory sizes using `pathlib.Path.rglob("*")` is unexpectedly slow compared to raw `os.scandir`, as `rglob` internally allocates many path objects.
**Action:** When calculating total size of a large number of directories, recursively traversing them with `os.scandir` yields significantly better performance. Remember to pass `follow_symlinks=False` to `is_dir()` to prevent infinite loops, but not to `is_file()` or `stat()` to preserve original symlink sizing behavior.

## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.