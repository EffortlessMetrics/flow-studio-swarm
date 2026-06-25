## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-25 - Pathlib iterdir performance
**Learning:** pathlib.Path.iterdir() followed by sorting is a significant performance bottleneck for large directories because it instantiates Path objects for every entry before sorting. os.scandir is much faster.
**Action:** Use os.scandir within a context manager to extract and sort lightweight string names, and only instantiate Path objects for the specific entries needed.
