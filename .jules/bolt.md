## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Optimize Directory Traversal in SpecManager
**Learning:** When retrieving run states from a large `runs` directory, `Path.iterdir()` creates a performance bottleneck because it unnecessarily instantiates full `Path` objects for every entry before filtering and sorting. This impacts the speed of `SpecManager.list_runs()`.
**Action:** Use `os.scandir()` as a context manager to extract lightweight string names and sort them lexicographically first. Only instantiate `Path` objects for the specific top N results being processed.
