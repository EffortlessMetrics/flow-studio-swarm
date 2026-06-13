## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-13 - Optimize Directory Traversal
**Learning:** Found a performance bottleneck where `pathlib.Path.iterdir()` was used instead of `os.scandir()` in a large directory, resulting in expensive `stat` system calls for each path object construction. `os.scandir()` is much faster because it leverages cached stat properties via `entry.is_file()` and `entry.name.endswith(...)`.
**Action:** Next time I encounter `iterdir` being used to process a large number of files, I will consider refactoring it to use `os.scandir()`.
