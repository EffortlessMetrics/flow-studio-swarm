## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-23 - Avoid Path.iterdir() for large directory scans
**Learning:** In python, `pathlib.Path.iterdir()` is a performance bottleneck for large directories because it instantiates `Path` objects for every file before sorting or filtering. `os.scandir()` within a context manager yields lightweight `DirEntry` strings directly, making filtered loops roughly 10x faster.
**Action:** Use `os.scandir()` to extract names when processing large directories, and only instantiate `Path` objects for the specific entries needed.
