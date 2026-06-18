## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-28 - os.scandir for directory traversal
**Learning:** `Path.iterdir()` is surprisingly slow for large directories (e.g. 10k items) because it instantiates `Path` objects for every single entry before sorting.
**Action:** Use `os.scandir()` within a context manager to extract names, sort the lightweight strings, and only instantiate `Path` objects for the entries actually needed.
