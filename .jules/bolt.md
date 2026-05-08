## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-05-08 - Fast Path Scanning with os.scandir
**Learning:** Python's `pathlib.Path.iterdir()` is surprisingly slow for large directories because it instantiates Path objects and makes expensive synchronous OS system stat calls.
**Action:** Always prefer `os.scandir()` instead of `iterdir()` in directory traversal loops. `os.scandir()` provides `os.DirEntry` objects, which internally cache the results of OS-level `.is_dir()`, `.is_file()`, and `.name` queries, resulting in 10-15x performance improvements for large directories. Remember to wrap `entry.path` with `Path()` only when necessary.
