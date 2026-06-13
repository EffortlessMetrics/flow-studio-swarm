## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-13 - Replace pathlib.Path.iterdir() with os.scandir()
**Learning:** In a heavily I/O bound path or when iterating large directories, `pathlib.Path.iterdir()` has significant overhead because it instantiates a full `Path` object for every directory entry. Additionally, `os.scandir()` caches stat information like `is_dir()` natively.
**Action:** Always prefer `os.scandir()` wrapped in a `with` statement when we only need entry names or basic stats like `is_dir()` across many items.
