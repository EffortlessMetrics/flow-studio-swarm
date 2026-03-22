## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-03-22 - Optimize recursive directory size calculation
**Learning:** When recursively traversing directories to calculate metrics like total size, replacing `pathlib.Path.rglob` with `os.scandir` yields significantly better performance.
**Action:** Use `os.scandir` (passing `follow_symlinks=False` to `is_dir()` to avoid infinite loops) for faster recursive directory traversal instead of `path.rglob`.