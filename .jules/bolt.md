## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-23 - Path.iterdir vs os.scandir Performance
**Learning:** In large directories with thousands of subdirectories, `pathlib.Path.iterdir()` followed by sorting is a significant performance bottleneck because it instantiates full `Path` objects for every entry before filtering and sorting. This causes measurable delays in endpoints that list runs.
**Action:** Use `os.scandir()` within a context manager to extract lightweight string names and filter/sort them before optionally instantiating `Path` objects only for the needed entries.
