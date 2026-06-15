## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-15 - Defer File Existence Checks for directory iteration
**Learning:** When using `os.scandir()` as an optimization over `iterdir()`, check entry.is_dir() directly on the DirEntry object to avoid expensive system stat calls later.
**Action:** Iterate through valid entries directly with `e.is_dir()` within the scandir context block before constructing Path objects.
