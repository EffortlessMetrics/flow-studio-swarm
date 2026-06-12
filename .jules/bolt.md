## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-12 - Replaced pathlib.iterdir with os.scandir for performance
**Learning:** Found an opportunity to improve performance by replacing `pathlib.Path.iterdir()` with `os.scandir()` in directory traversal operations across multiple files. `os.scandir` yields `os.DirEntry` objects which cache file attributes like `is_dir()` and `name`, avoiding expensive stat calls.
**Action:** When working with large directories, always prefer `os.scandir()` over `pathlib.Path.iterdir()` for better performance, especially when filtering by directory or name. Wrap `os.scandir` in a `with` statement and handle `OSError`.
