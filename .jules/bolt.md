## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-03-22 - Use os.scandir Instead of pathlib.Path.rglob for Directory Sizes
**Learning:** When recursively traversing directories to calculate metrics like total size, replacing `pathlib.Path.rglob` with `os.scandir` yields significantly better performance.
**Action:** Use `os.scandir` instead of `pathlib.Path.rglob` when recursively iterating directories for high-performance needs, making sure to use `follow_symlinks=False` on `is_dir()` to avoid infinite loops, but not on `is_file()` to maintain symlink sizing behavior.
