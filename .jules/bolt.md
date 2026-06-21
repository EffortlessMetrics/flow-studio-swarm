## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-21 - os.scandir vs pathlib.iterdir
**Learning:** When dealing with large directories, `pathlib.Path.iterdir()` followed by sorting is a significant performance bottleneck because it instantiates `Path` objects for every entry before sorting. Using `os.scandir()` within a context manager to extract and sort lightweight string names is much faster.
**Action:** Use `os.scandir()` when iterating over and sorting large directories, especially when checking for directory types with `entry.is_dir()`.
